"""
storage.py — Strato di persistenza SQLite compatibile Supabase + loader canonico Lead Engine IT/EU.

Funzioni principali:
- Bootstrap idempotente di dataset reali (data/*.csv), preset campagne (campaigns/*.json)
  ed export storici (exports_excel/, reports/, produzione/01_bozze_outbound/) senza mai
  sovrascrivere file originali del workspace.
- Normalizzazione canonica di ogni lead (isolamento PEC, LIA 3 fasi, product routing multi-prodotto).
- Cache in-memory basata su mtime file + suppression_list per risposte API istantanee.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from engine.compliance.lia_engine import DEFAULT_SUPPRESSION_CSV, SuppressionList, is_pec_email
from engine.routing.product_router import PRODUCT_CATALOG, route_lead_to_product
from engine.schemas.lead import LeadRecord
from src.clay_engine import format_full_whatsapp_draft
from src.config import (
    DATA_DIR,
    EXCEL_DIR,
    GDPR_OPTOUT_TEXT,
    REPORTS_DIR,
    ROOT_DIR,
    SENDER_IDENTITY,
    WEBSITE_CRAWL_CACHE_FILE,
)
from src.normalizers import (
    clean_company_website,
    is_anti_persona_retail,
    is_mobile_e164,
    is_strict_e164_italian,
    normalize_email,
    normalize_phone_e164,
)
from src.piva_validator import validate_piva

_LEADS_CACHE: Dict[str, Tuple[str, float, str, float, List[Dict[str, Any]]]] = {}
_CRAWL_CACHE: Optional[Dict[str, Any]] = None


def get_db_path() -> Path:
    env_path = os.getenv("LEAD_ENGINE_DB_PATH", "").strip()
    p = Path(env_path) if env_path else (DATA_DIR / "lead_engine_app.db")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def get_exports_dir() -> Path:
    env_dir = os.getenv("LEAD_ENGINE_EXPORTS_DIR", "").strip()
    d = Path(env_dir) if env_dir else (DATA_DIR / "exports")
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_runs_dir() -> Path:
    env_dir = os.getenv("LEAD_ENGINE_RUNS_DIR", "").strip()
    d = Path(env_dir) if env_dir else (DATA_DIR / "search_runs")
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_suppression_csv_path() -> Path:
    env_sup = os.getenv("LEAD_ENGINE_SUPPRESSION_PATH", "").strip()
    return Path(env_sup) if env_sup else DEFAULT_SUPPRESSION_CSV


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(get_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS saved_searches (
                id TEXT PRIMARY KEY,
                slug TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL CHECK (source_type IN ('dataset', 'preset', 'custom')),
                target_vertical TEXT NOT NULL DEFAULT '',
                ateco_codes_json TEXT NOT NULL DEFAULT '[]',
                search_queries_json TEXT NOT NULL DEFAULT '[]',
                geo_json TEXT NOT NULL DEFAULT '{}',
                product_target TEXT NOT NULL DEFAULT 'rsksystem',
                offer_summary TEXT NOT NULL DEFAULT '',
                enrichment_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'ready',
                status_note TEXT NOT NULL DEFAULT '',
                leads_count INTEGER NOT NULL DEFAULT 0,
                callable_count INTEGER NOT NULL DEFAULT 0,
                cost_eur REAL NOT NULL DEFAULT 0.0,
                estimated_cost_eur REAL NOT NULL DEFAULT 0.0,
                dataset_path TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                last_run_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS export_records (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                format TEXT NOT NULL CHECK (format IN ('CSV', 'XLSX', 'WEBHOOK_JSON', 'PDF', 'MARKDOWN')),
                search_id TEXT DEFAULT '',
                search_name TEXT NOT NULL DEFAULT '',
                file_path TEXT NOT NULL,
                row_count INTEGER NOT NULL DEFAULT 0,
                blocked_count INTEGER NOT NULL DEFAULT 0,
                filters_json TEXT NOT NULL DEFAULT '{}',
                approval_status TEXT NOT NULL DEFAULT 'DRAFT'
                    CHECK (approval_status IN ('DRAFT', 'APPROVED', 'DISPATCHED')),
                webhook_url TEXT NOT NULL DEFAULT '',
                size_bytes INTEGER NOT NULL DEFAULT 0,
                origin TEXT NOT NULL DEFAULT 'generated' CHECK (origin IN ('generated', 'legacy')),
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS outreach_approvals (
                lead_key TEXT PRIMARY KEY,
                company_name TEXT NOT NULL DEFAULT '',
                channel TEXT NOT NULL DEFAULT 'whatsapp',
                status TEXT NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('PENDING', 'APPROVED', 'SKIPPED')),
                notes TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
            """
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_rel_or_abs(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT_DIR.resolve()))
    except Exception:
        return str(path.resolve())


def resolve_stored_path(raw_path: str) -> Path:
    p = Path(raw_path)
    if p.is_absolute():
        return p.resolve()
    return (ROOT_DIR / p).resolve()


def _get_crawl_cache() -> Dict[str, Any]:
    global _CRAWL_CACHE
    if _CRAWL_CACHE is not None:
        return _CRAWL_CACHE
    if WEBSITE_CRAWL_CACHE_FILE.exists():
        try:
            _CRAWL_CACHE = json.loads(WEBSITE_CRAWL_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            _CRAWL_CACHE = {}
    else:
        _CRAWL_CACHE = {}
    return _CRAWL_CACHE


def _extract_tier_code(tier_str: str, icp_score: int) -> str:
    up = (tier_str or "").upper()
    if "TIER A" in up or up.strip() == "A":
        return "A"
    if "TIER B" in up or up.strip() == "B":
        return "B"
    if "TIER C" in up or up.strip() == "C":
        return "C"
    if icp_score >= 70:
        return "A"
    if icp_score >= 40:
        return "B"
    return "C"


def _split_csv_list(raw: str, empty_markers: Tuple[str, ...] = ("non rilevate", "non rilevato", "n/d", "-")) -> List[str]:
    if not raw:
        return []
    txt = str(raw).strip()
    if not txt or txt.lower() in empty_markers:
        return []
    return [p.strip() for p in re.split(r"[,|;]+", txt) if p.strip() and p.strip().lower() not in empty_markers]


def _lead_key(vat_id: str, phone_e164: str, company_name: str, city: str) -> str:
    base = (vat_id or "").strip().upper() or (phone_e164 or "").strip() or f"{company_name.strip().lower()}::{city.strip().lower()}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


def _normalize_legacy_csv_row(
    row: Dict[str, str],
    idx: int,
    search_id: str,
    suppression: SuppressionList,
    crawl_cache: Dict[str, Any],
) -> Dict[str, Any]:
    company_name = (row.get("Company Name") or row.get("company_name") or "").strip()
    city = (row.get("City") or row.get("city") or "").strip()
    area = (row.get("Area_Geografica") or "").strip()
    address = (row.get("Address") or "").strip()
    category = (row.get("Category") or "").strip()
    niche = (row.get("Nicchia_Target") or category or "Impiantistica").strip()
    website = clean_company_website(row.get("Website") or "")

    raw_phone = row.get("Phone") or row.get("phone_e164") or ""
    p1, p2_extracted = normalize_phone_e164(raw_phone)
    sec_raw = (row.get("Phone_Secondary") or "").strip()
    p_sec = sec_raw or p2_extracted
    if p_sec and not p_sec.startswith("+"):
        sec_norm, _ = normalize_phone_e164(p_sec)
        p_sec = sec_norm

    phone_type = "Mobile" if is_mobile_e164(p1) else ("Fisso" if is_strict_e164_italian(p1) else "Unknown")
    callable_flag = bool(is_strict_e164_italian(p1))

    raw_email = normalize_email(row.get("Email") or "")
    pec_addr = ""
    pec_blocked = False
    if raw_email and is_pec_email(raw_email):
        pec_addr = raw_email
        raw_email = ""
        pec_blocked = True

    vat_raw = (row.get("Partita_IVA") or "").strip().upper()
    has_valid_piva = bool(vat_raw and validate_piva(vat_raw))
    if has_valid_piva and not vat_raw.startswith("IT"):
        vat_raw = f"IT{vat_raw}"

    cna_status = (row.get("Stato_CNA") or "").strip()
    cna_eligible_50 = "NON ASSOCIATO" in cna_status.upper() or not cna_status

    try:
        icp_score = int(float(row.get("ICP_Score") or 0))
    except Exception:
        icp_score = 0
    lead_tier = (row.get("Lead_Tier") or "").strip()
    tier_code = _extract_tier_code(lead_tier, icp_score)
    if not lead_tier:
        lead_tier = f"Tier {tier_code}"

    brands = _split_csv_list(row.get("Marchi_Rilevati") or "")
    brands_verified = (row.get("Marchi_Verificati") or "").strip().upper() == "SI" or bool(brands)
    certifications = _split_csv_list(row.get("Certificazioni_Rilevate") or "")
    h24_raw = (row.get("Servizio_H24") or "").strip()
    is_h24 = h24_raw.upper().startswith("SI")
    trigger_signal = (row.get("Trigger_Segnale") or "").strip()

    routed = route_lead_to_product(
        company_name=company_name,
        category=category,
        niche=niche,
        website_text=" ".join(brands),
    )

    icebreaker = (row.get("Icebreaker_1to1") or "").strip()
    if not icebreaker:
        icebreaker = (
            f"Buongiorno {company_name}, vi contatto da TecnicoLIVE (Sinergia Rete d'Imprese). "
            f"Per le imprese di {niche} a {city or 'Catania'}, con la convenzione CNA Catania "
            f"attivate l'assistente vocale AI e l'associazione CNA al 50% per il primo anno."
        )
    wa_draft = (row.get("Messaggio_WhatsApp_Completo") or "").strip() or format_full_whatsapp_draft(icebreaker)

    # Conformità GDPR LIA 3 fasi deterministica e allineata a lia_engine.py
    is_sup = suppression.is_suppressed(phone_e164=p1, email=raw_email, vat_id=vat_raw)
    is_gdo = is_anti_persona_retail(company_name, category, website)
    purpose_ok = bool(company_name) and not is_gdo
    necessity_ok = bool(company_name) and bool(vat_raw or website or city) and bool(p1 or raw_email)
    balancing_ok = not is_sup
    rpo_required = is_strict_e164_italian(p1)

    if is_sup or not purpose_ok:
        lia_status = "BLOCKED"
    elif not necessity_ok:
        lia_status = "REVIEW_REQUIRED"
    else:
        lia_status = "PASS"

    crawl_info = {}
    if website:
        for k, v in crawl_cache.items():
            if website.replace("https://", "").replace("http://", "").rstrip("/") in k:
                crawl_info = v if isinstance(v, dict) else {}
                break

    return {
        "id": f"{search_id}:{idx}",
        "lead_key": _lead_key(vat_raw, p1, company_name, city),
        "search_id": search_id,
        "company_name": company_name,
        "vat_id": vat_raw,
        "has_valid_piva": has_valid_piva,
        "vies_valid": None,
        "ateco_code": "",
        "forma_giuridica": "",
        "country_code": "IT",
        "province": "CT" if area else "",
        "city": city,
        "area_geografica": area,
        "istat_code": "",
        "postal_code": "",
        "address": address,
        "phone_e164": p1,
        "phone_secondary": p_sec,
        "phone_type": phone_type,
        "callable": callable_flag,
        "email": raw_email,
        "email_mx_valid": None,
        "pec": pec_addr,
        "website": website,
        "category": category,
        "niche": niche,
        "cna_status": cna_status,
        "cna_eligible_50": cna_eligible_50,
        "icp_score": icp_score,
        "lead_tier": lead_tier,
        "tier_code": tier_code,
        "brands": brands,
        "brands_verified": brands_verified,
        "certifications": certifications,
        "is_h24": is_h24,
        "trigger_signal": trigger_signal,
        "recommended_product": routed["product_key"],
        "recommended_product_name": routed["product_name"],
        "recommended_product_url": routed["product_url"],
        "routing_rationale": routed["rationale"],
        "recommended_action": (row.get("Azione_Commerciale_Consigliata") or routed["cta"]).strip(),
        "icebreaker_1to1": icebreaker,
        "whatsapp_draft": wa_draft,
        "gdpr_sender": SENDER_IDENTITY,
        "gdpr_optout": (row.get("Footer_GDPR_OptOut") or GDPR_OPTOUT_TEXT).strip(),
        "lia_status": lia_status,
        "lia_purpose_ok": purpose_ok,
        "lia_necessity_ok": necessity_ok,
        "lia_balancing_ok": balancing_ok,
        "pec_blocked": pec_blocked,
        "rpo_required": rpo_required,
        "suppressed": is_sup,
        "tech_audit": {
            "crawl_status": crawl_info.get("crawl_status", "CACHED" if crawl_info else "NOT_SCANNED"),
            "pages_scanned": crawl_info.get("pages_scanned", 0),
            "piva_source": (row.get("Fonte_PIVA") or crawl_info.get("piva_source") or "").strip(),
            "http_status": 200 if crawl_info.get("crawl_status") == "SUCCESS" else 0,
            "has_ssl": website.startswith("https://") if website else False,
            "cms_stack": "Unknown",
            "tracking_pixels": [],
            "has_whatsapp_cta": False,
            "has_booking_or_quote_form": False,
        },
        "ai_qualification": {
            "model_used": "clay_engine_semantic",
            "business_model": "B2B/B2C",
            "detected_pain_points": [trigger_signal] if trigger_signal else [],
            "evidence_quotes": brands,
            "outreach_angle": (row.get("Pitch_Commerciale_TecnicoLIVE") or routed["core_pitch"]).strip(),
        },
        "data_scoperta": (row.get("Data_Scoperta") or "").strip(),
    }


def _normalize_lead_record_dict(
    raw: Dict[str, Any],
    idx: int,
    search_id: str,
    suppression: SuppressionList,
) -> Dict[str, Any]:
    company_name = str(raw.get("company_name") or "").strip()
    city = str(raw.get("city") or "").strip()
    vat_id = str(raw.get("vat_id") or "").strip().upper()
    p1 = str(raw.get("phone_e164") or "").strip()
    raw_email = normalize_email(raw.get("email") or "")
    pec_addr = str(raw.get("pec") or "").strip().lower()
    pec_blocked = bool(pec_addr)
    if raw_email and is_pec_email(raw_email):
        if not pec_addr:
            pec_addr = raw_email
        raw_email = ""
        pec_blocked = True

    ai_q = raw.get("ai_qualification") or {}
    tech = raw.get("tech_audit") or {}
    reg = raw.get("registry") or {}
    lia = raw.get("lia") or {}

    icp_score = int(ai_q.get("icp_fit_score") or 0)
    lead_tier = str(ai_q.get("lead_tier") or f"Tier {_extract_tier_code('', icp_score)}")
    tier_code = _extract_tier_code(lead_tier, icp_score)

    prod_key = str(ai_q.get("recommended_product") or "rsksystem")
    prod = PRODUCT_CATALOG.get(prod_key, PRODUCT_CATALOG["rsksystem"])

    is_sup = suppression.is_suppressed(phone_e164=p1, email=raw_email, vat_id=vat_id)
    lia_status = "BLOCKED" if is_sup else str(lia.get("status") or ("PASS" if (p1 or raw_email) else "REVIEW_REQUIRED"))
    icebreaker = str(ai_q.get("icebreaker_1to1") or ai_q.get("outreach_angle") or "")
    wa_draft = format_full_whatsapp_draft(icebreaker or f"Buongiorno {company_name}, {prod['core_pitch']}")

    return {
        "id": f"{search_id}:{idx}",
        "lead_key": _lead_key(vat_id, p1, company_name, city),
        "search_id": search_id,
        "company_name": company_name,
        "vat_id": vat_id,
        "has_valid_piva": bool(vat_id and validate_piva(vat_id)),
        "vies_valid": reg.get("vies_valid"),
        "ateco_code": str(reg.get("ateco_code") or ""),
        "forma_giuridica": str(reg.get("forma_giuridica") or ""),
        "country_code": str(raw.get("country_code") or "IT"),
        "province": str(raw.get("province") or ""),
        "city": city,
        "area_geografica": str(raw.get("region") or raw.get("province") or ""),
        "istat_code": str(raw.get("istat_code") or ""),
        "postal_code": str(raw.get("postal_code") or ""),
        "address": str(raw.get("address") or ""),
        "phone_e164": p1,
        "phone_secondary": str(raw.get("phone_secondary") or ""),
        "phone_type": str(raw.get("phone_type") or ("Mobile" if is_mobile_e164(p1) else ("Fisso" if p1 else "Unknown"))),
        "callable": bool(is_strict_e164_italian(p1)),
        "email": raw_email,
        "email_mx_valid": raw.get("email_mx_valid") if raw.get("email_mx_valid") is not None else tech.get("email_mx_valid"),
        "pec": pec_addr,
        "website": str(raw.get("website") or ""),
        "category": str(raw.get("category") or ""),
        "niche": str(raw.get("niche") or raw.get("category") or ""),
        "cna_status": "",
        "cna_eligible_50": prod_key == "tecnicolive",
        "icp_score": icp_score,
        "lead_tier": lead_tier,
        "tier_code": tier_code,
        "brands": list(ai_q.get("evidence_quotes") or []),
        "brands_verified": bool(ai_q.get("evidence_quotes")),
        "certifications": list(reg.get("albi_certificazioni") or []),
        "is_h24": False,
        "trigger_signal": str(ai_q.get("outreach_angle") or ""),
        "recommended_product": prod["key"],
        "recommended_product_name": prod["name"],
        "recommended_product_url": prod["url"],
        "routing_rationale": str(ai_q.get("outreach_angle") or prod["core_pitch"]),
        "recommended_action": prod["cta"],
        "icebreaker_1to1": icebreaker,
        "whatsapp_draft": wa_draft,
        "gdpr_sender": SENDER_IDENTITY,
        "gdpr_optout": GDPR_OPTOUT_TEXT,
        "lia_status": lia_status,
        "lia_purpose_ok": bool((lia.get("purpose_test") or {}).get("passed", True)),
        "lia_necessity_ok": bool((lia.get("necessity_test") or {}).get("passed", bool(p1 or raw_email))),
        "lia_balancing_ok": not is_sup,
        "pec_blocked": pec_blocked,
        "rpo_required": is_strict_e164_italian(p1),
        "suppressed": is_sup,
        "tech_audit": tech,
        "ai_qualification": ai_q,
        "data_scoperta": "",
    }


def _count_csv_quick(csv_path: Path) -> Tuple[int, int]:
    if not csv_path.exists():
        return 0, 0
    total = 0
    callable_cnt = 0
    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                total += 1
                ph = (row.get("Phone") or row.get("phone_e164") or "").strip()
                if ph.startswith("+39"):
                    callable_cnt += 1
    except Exception:
        return 0, 0
    return total, callable_cnt


def _count_excel_rows(xlsx_path: Path) -> int:
    try:
        import openpyxl

        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        ws = wb.active
        count = max(0, (ws.max_row or 1) - 1) if ws else 0
        wb.close()
        return count
    except Exception:
        return 0


def bootstrap_workspace_records() -> None:
    """Indicizza dataset CSV reali, preset JSON ed export storici in modo idempotente."""
    init_db()
    now = _now_iso()

    builtin_datasets = [
        (
            "ds-outbound-tecnicolive",
            "outbound-chiamabili-e164",
            "Campagna Outbound Chiamabili (E.164) — Impiantisti Catania",
            "Termoidraulica, Climatizzazione & Elettrici",
            ["43.22.01", "43.22.02", "43.21.01"],
            ["Catania", "Acireale", "Misterbianco", "Paternò", "Giarre"],
            "tecnicolive",
            "TecnicoLIVE Voice AI H24 (169€/269€/369€) + Associazione CNA Catania 50% 1° anno",
            DATA_DIR / "campagna_outbound_tecnicolive.csv",
        ),
        (
            "ds-master-clean",
            "archivio-master-923",
            "Archivio Master Aziende Pulite — Provincia di Catania",
            "Impiantistica & Servizi Tecnici B2B",
            ["43.22.01", "43.21.01", "43.29.01"],
            ["Catania e Provincia (58 Comuni ISTAT)"],
            "tecnicolive",
            "Lista master validata (Zero Hallucination, anti-GDO, P.IVA Luhn, telefoni E.164)",
            DATA_DIR / "tutte_le_lead.csv",
        ),
        (
            "ds-termoidraulica",
            "verticale-termoidraulica-ct",
            "Verticale Termoidraulica, Caldaie & Clima — Catania",
            "Termoidraulica & Climatizzazione",
            ["43.22.01", "43.22.02"],
            ["Catania", "Acireale", "Etna", "Ionica"],
            "tecnicolive",
            "Focus caldaisti CITEL Sicilia, installatori F-Gas e assistenza multimarca",
            DATA_DIR / "termoidraulica_catania_provincia.csv",
        ),
        (
            "ds-da-arricchire",
            "coda-arricchimento-no-tel",
            "Aziende Senza Telefono — Coda Arricchimento Places / Openapi",
            "Impiantistica (Solo Sito/P.IVA)",
            ["43.22.01", "43.21.01"],
            ["Catania e Provincia"],
            "tecnicolive",
            "Lead con anagrafica verificata prive di recapito telefonico (in attesa di enrichment L1/L3)",
            DATA_DIR / "da_arricchire_contatti.csv",
        ),
    ]

    with get_connection() as conn:
        for ds_id, slug, name, vert, ateco, munis, prod, offer, path in builtin_datasets:
            if not path.exists():
                continue
            total_c, call_c = _count_csv_quick(path)
            mtime_iso = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
            geo_json = json.dumps({"country_code": "IT", "province_code": "CT", "municipalities": munis}, ensure_ascii=False)
            enrich_json = json.dumps({"enable_l1_tech_audit": True, "enable_l1_vies": True, "enable_l2_gemini_ai": False, "enable_l3_openapi_registry": False})
            conn.execute(
                """
                INSERT INTO saved_searches (
                    id, slug, name, source_type, target_vertical, ateco_codes_json,
                    search_queries_json, geo_json, product_target, offer_summary,
                    enrichment_json, status, status_note, leads_count, callable_count,
                    cost_eur, estimated_cost_eur, dataset_path, created_at, last_run_at
                ) VALUES (?, ?, ?, 'dataset', ?, ?, '[]', ?, ?, ?, ?, 'ready', ?, ?, ?, 0.0, 0.0, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    leads_count = excluded.leads_count,
                    callable_count = excluded.callable_count,
                    dataset_path = excluded.dataset_path
                """,
                (
                    ds_id,
                    slug,
                    name,
                    vert,
                    json.dumps(ateco),
                    geo_json,
                    prod,
                    offer,
                    enrich_json,
                    "Archivio locale verificato e normalizzato",
                    total_c,
                    call_c,
                    _safe_rel_or_abs(path),
                    mtime_iso,
                    mtime_iso,
                ),
            )

        # Indicizza preset campagne (campaigns/*.json)
        campaigns_dir = ROOT_DIR / "campaigns"
        if campaigns_dir.exists():
            for pf in sorted(campaigns_dir.glob("*.json")):
                try:
                    pdata = json.loads(pf.read_text(encoding="utf-8"))
                except Exception:
                    continue
                cid = str(pdata.get("campaign_id") or pf.stem)
                pid = f"preset-{cid}"
                run_file = get_runs_dir() / f"{pid}.json"
                run_leads_cnt = 0
                run_call_cnt = 0
                run_status = "ready"
                if run_file.exists():
                    try:
                        rdata = json.loads(run_file.read_text(encoding="utf-8"))
                        run_leads_cnt = len(rdata)
                        run_call_cnt = sum(1 for item in rdata if item.get("phone_e164"))
                    except Exception:
                        pass

                conn.execute(
                    """
                    INSERT INTO saved_searches (
                        id, slug, name, source_type, target_vertical, ateco_codes_json,
                        search_queries_json, geo_json, product_target, offer_summary,
                        enrichment_json, status, status_note, leads_count, callable_count,
                        cost_eur, estimated_cost_eur, dataset_path, created_at, last_run_at
                    ) VALUES (?, ?, ?, 'preset', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, ?, ?, ?)
                    ON CONFLICT(id) DO NOTHING
                    """,
                    (
                        pid,
                        cid,
                        str(pdata.get("name") or pf.stem),
                        str(pdata.get("target_vertical") or ""),
                        json.dumps(pdata.get("ateco_codes") or []),
                        json.dumps(pdata.get("search_queries") or [], ensure_ascii=False),
                        json.dumps(pdata.get("geo") or {}, ensure_ascii=False),
                        str(pdata.get("default_upsell_product") or "rsksystem"),
                        str(pdata.get("offer_summary") or ""),
                        json.dumps(pdata.get("enrichment") or {}),
                        run_status,
                        "Playbook verticale multi-settore (campaigns/*.json)",
                        run_leads_cnt,
                        run_call_cnt,
                        _safe_rel_or_abs(run_file) if run_file.exists() else "",
                        now,
                        now,
                    ),
                )

        # Indicizza export storici (exports_excel/, reports/, produzione/01_bozze_outbound/)
        legacy_candidates: List[Tuple[Path, str, str]] = []
        if EXCEL_DIR.exists():
            for f in sorted(EXCEL_DIR.glob("*.xlsx")):
                legacy_candidates.append((f, "XLSX", "Export Excel Operativo CNA/TecnicoLIVE"))
        if REPORTS_DIR.exists():
            for f in sorted(REPORTS_DIR.glob("*.pdf")):
                legacy_candidates.append((f, "PDF", "Report Strategico PDF"))
        bozze_dir = ROOT_DIR / "produzione" / "01_bozze_outbound"
        if bozze_dir.exists():
            for f in sorted(bozze_dir.glob("*")):
                if f.is_file():
                    fmt = "WEBHOOK_JSON" if f.suffix.lower() == ".json" else "MARKDOWN"
                    legacy_candidates.append((f, fmt, "Bozza Outbound HITL"))

        for fpath, fmt, label in legacy_candidates:
            exp_id = f"leg-{hashlib.sha1(fpath.name.encode('utf-8')).hexdigest()[:12]}"
            size_b = fpath.stat().st_size
            mtime_iso = datetime.fromtimestamp(fpath.stat().st_mtime, tz=timezone.utc).isoformat()
            row_cnt = _count_excel_rows(fpath) if fmt == "XLSX" else 0
            conn.execute(
                """
                INSERT INTO export_records (
                    id, filename, format, search_id, search_name, file_path,
                    row_count, blocked_count, filters_json, approval_status,
                    webhook_url, size_bytes, origin, created_at
                ) VALUES (?, ?, ?, '', ?, ?, ?, 0, '{}', 'DRAFT', '', ?, 'legacy', ?)
                ON CONFLICT(id) DO UPDATE SET
                    size_bytes = excluded.size_bytes,
                    row_count = CASE WHEN excluded.row_count > 0 THEN excluded.row_count ELSE export_records.row_count END
                """,
                (exp_id, fpath.name, fmt, label, _safe_rel_or_abs(fpath), row_cnt, size_b, mtime_iso),
            )


def _row_to_search_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "source_type": row["source_type"],
        "target_vertical": row["target_vertical"],
        "ateco_codes": json.loads(row["ateco_codes_json"] or "[]"),
        "search_queries": json.loads(row["search_queries_json"] or "[]"),
        "geo": json.loads(row["geo_json"] or "{}"),
        "product_target": row["product_target"],
        "offer_summary": row["offer_summary"],
        "enrichment": json.loads(row["enrichment_json"] or "{}"),
        "status": row["status"],
        "status_note": row["status_note"],
        "leads_count": row["leads_count"],
        "callable_count": row["callable_count"],
        "cost_eur": row["cost_eur"],
        "estimated_cost_eur": row["estimated_cost_eur"],
        "dataset_path": row["dataset_path"],
        "created_at": row["created_at"],
        "last_run_at": row["last_run_at"],
    }


def list_searches() -> List[Dict[str, Any]]:
    bootstrap_workspace_records()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM saved_searches
            ORDER BY
                CASE source_type WHEN 'custom' THEN 0 WHEN 'dataset' THEN 1 ELSE 2 END,
                last_run_at DESC, created_at DESC
            """
        ).fetchall()
        return [_row_to_search_dict(r) for r in rows]


def get_search(search_id: str) -> Optional[Dict[str, Any]]:
    bootstrap_workspace_records()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM saved_searches WHERE id = ?", (search_id,)).fetchone()
        return _row_to_search_dict(row) if row else None


def estimate_search_cost(enrichment: Dict[str, Any], expected_leads: int = 40) -> float:
    l2_cost = (0.0008 * expected_leads) if enrichment.get("enable_l2_gemini_ai") else 0.0
    l3_cost = float(enrichment.get("max_l3_budget_eur") or 0.0) if enrichment.get("enable_l3_openapi_registry") else 0.0
    return round(l2_cost + l3_cost, 2)


def create_custom_search(payload: Dict[str, Any]) -> Dict[str, Any]:
    bootstrap_workspace_records()
    now = _now_iso()
    raw_name = str(payload.get("name") or "Nuova Ricerca").strip()
    slug_base = re.sub(r"[^a-z0-9]+", "-", raw_name.lower()).strip("-") or "ricerca"
    uid = hashlib.sha1(f"{raw_name}:{now}".encode("utf-8")).hexdigest()[:8]
    sid = f"srch-{uid}"
    slug = f"{slug_base[:36]}-{uid}"

    enrichment = payload.get("enrichment") or {}
    max_results = int(payload.get("max_results_per_query") or 20)
    queries = list(payload.get("search_queries") or [])
    expected_leads = max(10, min(120, max_results * max(1, len(queries))))
    est_cost = estimate_search_cost(enrichment, expected_leads=expected_leads)

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO saved_searches (
                id, slug, name, source_type, target_vertical, ateco_codes_json,
                search_queries_json, geo_json, product_target, offer_summary,
                enrichment_json, status, status_note, leads_count, callable_count,
                cost_eur, estimated_cost_eur, dataset_path, created_at, last_run_at
            ) VALUES (?, ?, ?, 'custom', ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0.0, ?, '', ?, ?)
            """,
            (
                sid,
                slug,
                raw_name,
                str(payload.get("target_vertical") or ""),
                json.dumps(payload.get("ateco_codes") or []),
                json.dumps(queries, ensure_ascii=False),
                json.dumps(payload.get("geo") or {}, ensure_ascii=False),
                str(payload.get("product_target") or "rsksystem"),
                str(payload.get("offer_summary") or ""),
                json.dumps(enrichment),
                "running" if payload.get("run_now") else "draft",
                "Inizializzazione ricerca..." if payload.get("run_now") else "Bozza salvata (pronta per il lancio)",
                est_cost,
                now,
                now,
            ),
        )
    return get_search(sid) or {}


def update_search_run_state(
    search_id: str,
    status: str,
    status_note: str = "",
    leads_count: Optional[int] = None,
    callable_count: Optional[int] = None,
    cost_eur: Optional[float] = None,
    dataset_path: Optional[str] = None,
) -> None:
    now = _now_iso()
    with get_connection() as conn:
        existing = conn.execute("SELECT * FROM saved_searches WHERE id = ?", (search_id,)).fetchone()
        if not existing:
            return
        conn.execute(
            """
            UPDATE saved_searches SET
                status = ?,
                status_note = ?,
                leads_count = ?,
                callable_count = ?,
                cost_eur = ?,
                dataset_path = ?,
                last_run_at = ?
            WHERE id = ?
            """,
            (
                status,
                status_note,
                leads_count if leads_count is not None else existing["leads_count"],
                callable_count if callable_count is not None else existing["callable_count"],
                cost_eur if cost_eur is not None else existing["cost_eur"],
                dataset_path if dataset_path is not None else existing["dataset_path"],
                now,
                search_id,
            ),
        )


def duplicate_search(search_id: str) -> Optional[Dict[str, Any]]:
    orig = get_search(search_id)
    if not orig:
        return None
    return create_custom_search(
        {
            "name": f"{orig['name']} (Copia)",
            "target_vertical": orig["target_vertical"],
            "ateco_codes": orig["ateco_codes"],
            "search_queries": orig["search_queries"],
            "geo": orig["geo"],
            "product_target": orig["product_target"],
            "offer_summary": orig["offer_summary"],
            "enrichment": orig["enrichment"],
            "run_now": False,
        }
    )


def delete_custom_search(search_id: str) -> Tuple[bool, str]:
    rec = get_search(search_id)
    if not rec:
        return False, "Ricerca non trovata."
    if rec["source_type"] != "custom":
        return False, "Gli archivi master e i playbook di sistema non possono essere eliminati."
    run_file = get_runs_dir() / f"{search_id}.json"
    if run_file.exists():
        run_file.unlink(missing_ok=True)
    _LEADS_CACHE.pop(search_id, None)
    with get_connection() as conn:
        conn.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))
    return True, "Ricerca eliminata."


def save_search_run_leads(search_id: str, leads: List[LeadRecord], cost_eur: float = 0.0, note: str = "") -> Path:
    runs_dir = get_runs_dir()
    out_path = runs_dir / f"{search_id}.json"
    serialized = [ld.model_dump() for ld in leads]
    out_path.write_text(json.dumps(serialized, ensure_ascii=False, indent=2), encoding="utf-8")
    callable_cnt = sum(1 for ld in leads if is_strict_e164_italian(ld.phone_e164))
    _LEADS_CACHE.pop(search_id, None)
    update_search_run_state(
        search_id=search_id,
        status="ready",
        status_note=note or f"Completata: {len(leads)} aziende qualificate",
        leads_count=len(leads),
        callable_count=callable_cnt,
        cost_eur=cost_eur,
        dataset_path=_safe_rel_or_abs(out_path),
    )
    return out_path


def load_search_leads(search_id: str = "ds-outbound-tecnicolive") -> List[Dict[str, Any]]:
    search = get_search(search_id)
    if not search or not search["dataset_path"]:
        return []
    path = resolve_stored_path(search["dataset_path"])
    if not path.exists():
        return []

    sup_path = get_suppression_csv_path()
    sup_mtime = sup_path.stat().st_mtime if sup_path.exists() else 0.0
    file_mtime = path.stat().st_mtime

    cached = _LEADS_CACHE.get(search_id)
    if (
        cached
        and cached[0] == str(path)
        and cached[1] == file_mtime
        and cached[2] == str(sup_path)
        and cached[3] == sup_mtime
    ):
        return cached[4]

    suppression = SuppressionList(csv_path=sup_path)
    crawl_cache = _get_crawl_cache()
    normalized: List[Dict[str, Any]] = []

    if path.suffix.lower() == ".json":
        try:
            raw_list = json.loads(path.read_text(encoding="utf-8"))
            for idx, item in enumerate(raw_list):
                if isinstance(item, dict):
                    normalized.append(_normalize_lead_record_dict(item, idx, search_id, suppression))
        except Exception:
            normalized = []
    else:
        try:
            with open(path, encoding="utf-8-sig", newline="") as f:
                for idx, row in enumerate(csv.DictReader(f)):
                    normalized.append(_normalize_legacy_csv_row(row, idx, search_id, suppression, crawl_cache))
        except Exception:
            normalized = []

    _LEADS_CACHE[search_id] = (str(path), file_mtime, str(sup_path), sup_mtime, normalized)
    return normalized


# ── EXPORT ARCHIVE ──────────────────────────────────────────────────────────────

def _row_to_export_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "filename": row["filename"],
        "format": row["format"],
        "search_id": row["search_id"],
        "search_name": row["search_name"],
        "file_path": row["file_path"],
        "row_count": row["row_count"],
        "blocked_count": row["blocked_count"],
        "filters": json.loads(row["filters_json"] or "{}"),
        "approval_status": row["approval_status"],
        "webhook_url": row["webhook_url"],
        "size_bytes": row["size_bytes"],
        "origin": row["origin"],
        "created_at": row["created_at"],
    }


def list_exports(fmt: str = "", search_id: str = "", approval_status: str = "") -> List[Dict[str, Any]]:
    bootstrap_workspace_records()
    query = "SELECT * FROM export_records WHERE 1=1"
    params: List[Any] = []
    if fmt:
        query += " AND format = ?"
        params.append(fmt.upper())
    if search_id:
        query += " AND search_id = ?"
        params.append(search_id)
    if approval_status:
        query += " AND approval_status = ?"
        params.append(approval_status.upper())
    query += " ORDER BY created_at DESC"
    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_export_dict(r) for r in rows]


def get_export(export_id: str) -> Optional[Dict[str, Any]]:
    bootstrap_workspace_records()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM export_records WHERE id = ?", (export_id,)).fetchone()
        return _row_to_export_dict(row) if row else None


def _leads_for_export_table(leads: List[Dict[str, Any]]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for ld in leads:
        safe_email = "" if is_pec_email(ld.get("email", "")) else ld.get("email", "")
        rows.append(
            {
                "Company_Name": ld.get("company_name", ""),
                "Partita_IVA": ld.get("vat_id", ""),
                "ATECO_Code": ld.get("ateco_code", ""),
                "VIES_Valid": "" if ld.get("vies_valid") is None else ("SI" if ld.get("vies_valid") else "NO"),
                "Country": ld.get("country_code", "IT"),
                "City": ld.get("city", ""),
                "Area_Geografica": ld.get("area_geografica", ""),
                "Address": ld.get("address", ""),
                "Phone_E164": ld.get("phone_e164", ""),
                "Phone_Type": ld.get("phone_type", "Unknown"),
                "Email_Aziendale": safe_email,
                "PEC_Solo_Registro": ld.get("pec", ""),
                "Website": ld.get("website", ""),
                "Nicchia_Target": ld.get("niche", ""),
                "Stato_CNA": ld.get("cna_status", ""),
                "ICP_Score": ld.get("icp_score", 0),
                "Lead_Tier": ld.get("lead_tier", ""),
                "Recommended_Product": ld.get("recommended_product", ""),
                "Recommended_Product_Name": ld.get("recommended_product_name", ""),
                "Marchi_Rilevati": ", ".join(ld.get("brands") or []),
                "Trigger_Segnale": ld.get("trigger_signal", ""),
                "Icebreaker_1to1": ld.get("icebreaker_1to1", ""),
                "Messaggio_WhatsApp_Completo": ld.get("whatsapp_draft", ""),
                "LIA_Status": ld.get("lia_status", "REVIEW_REQUIRED"),
                "PEC_Blocked": "SI" if ld.get("pec_blocked") else "NO",
                "RPO_Check_Required": "SI" if ld.get("rpo_required") else "NO",
                "GDPR_Sender": ld.get("gdpr_sender", SENDER_IDENTITY),
                "GDPR_OptOut": ld.get("gdpr_optout", GDPR_OPTOUT_TEXT),
            }
        )
    return pd.DataFrame(rows)


def create_export_from_leads(
    search_id: str,
    search_name: str,
    fmt: str,
    candidate_leads: List[Dict[str, Any]],
    filters_applied: Optional[Dict[str, Any]] = None,
    filename_prefix: str = "",
) -> Dict[str, Any]:
    """
    Genera un file export conforme GDPR (scarta BLOCKED/suppressed e isola PEC)
    e lo salva permanentemente in Archivio Export.
    """
    init_db()
    fmt_up = fmt.upper()
    if fmt_up not in ("CSV", "XLSX", "WEBHOOK_JSON"):
        raise ValueError(f"Formato export non supportato: {fmt}")

    eligible: List[Dict[str, Any]] = []
    blocked_count = 0
    for ld in candidate_leads:
        if ld.get("lia_status") == "BLOCKED" or ld.get("suppressed"):
            blocked_count += 1
            continue
        eligible.append(ld)

    now_dt = datetime.now(timezone.utc)
    ts = now_dt.strftime("%Y%m%d_%H%M%S")
    safe_prefix = re.sub(r"[^a-zA-Z0-9_-]+", "_", filename_prefix or search_id or "export").strip("_")[:48] or "export"
    uid = hashlib.sha1(f"{safe_prefix}:{ts}:{len(eligible)}".encode("utf-8")).hexdigest()[:6]

    exports_dir = get_exports_dir()
    ext = "csv" if fmt_up == "CSV" else ("xlsx" if fmt_up == "XLSX" else "json")
    filename = f"{safe_prefix}_{ts}_{uid}.{ext}"
    out_path = (exports_dir / filename).resolve()

    if fmt_up == "CSV":
        df = _leads_for_export_table(eligible)
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
    elif fmt_up == "XLSX":
        df = _leads_for_export_table(eligible)
        df.to_excel(out_path, index=False, engine="openpyxl")
    else:
        contacts_payload = []
        for ld in eligible:
            safe_email = "" if is_pec_email(ld.get("email", "")) else ld.get("email", "")
            if not (ld.get("phone_e164") or safe_email):
                blocked_count += 1
                continue
            contacts_payload.append(
                {
                    "company_name": ld.get("company_name", ""),
                    "vat_id": ld.get("vat_id", ""),
                    "country": ld.get("country_code", "IT"),
                    "city": ld.get("city", ""),
                    "address": ld.get("address", ""),
                    "phone": ld.get("phone_e164", ""),
                    "email": safe_email,
                    "website": ld.get("website", ""),
                    "tags": [
                        f"Verticale: {ld.get('niche') or 'PMI'}",
                        f"Prodotto: {ld.get('recommended_product') or 'rsksystem'}",
                        f"Tier: {ld.get('tier_code') or 'C'}",
                        f"LIA: {ld.get('lia_status') or 'REVIEW_REQUIRED'}",
                    ],
                    "custom_fields": {
                        "icp_score": ld.get("icp_score", 0),
                        "recommended_product_url": ld.get("recommended_product_url", ""),
                        "icebreaker_1to1": ld.get("icebreaker_1to1", ""),
                        "rpo_check_required": bool(ld.get("rpo_required")),
                        "gdpr_sender": ld.get("gdpr_sender", SENDER_IDENTITY),
                        "gdpr_optout": ld.get("gdpr_optout", GDPR_OPTOUT_TEXT),
                    },
                }
            )
        payload = {
            "search_id": search_id,
            "search_name": search_name,
            "generated_at_utc": now_dt.isoformat(),
            "human_in_the_loop_required": True,
            "eligible_count": len(contacts_payload),
            "skipped_blocked_count": blocked_count,
            "contacts": contacts_payload,
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        eligible_len = len(contacts_payload)
    if fmt_up != "WEBHOOK_JSON":
        eligible_len = len(eligible)

    exp_id = f"exp-{uid}-{int(now_dt.timestamp()) % 100000}"
    size_b = out_path.stat().st_size if out_path.exists() else 0
    created_iso = now_dt.isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO export_records (
                id, filename, format, search_id, search_name, file_path,
                row_count, blocked_count, filters_json, approval_status,
                webhook_url, size_bytes, origin, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', '', ?, 'generated', ?)
            """,
            (
                exp_id,
                filename,
                fmt_up,
                search_id,
                search_name,
                _safe_rel_or_abs(out_path),
                eligible_len,
                blocked_count,
                json.dumps(filters_applied or {}, ensure_ascii=False),
                size_b,
                created_iso,
            ),
        )
    return get_export(exp_id) or {}


def update_export_approval(export_id: str, approval_status: str, webhook_url: str = "") -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        conn.execute(
            "UPDATE export_records SET approval_status = ?, webhook_url = COALESCE(NULLIF(?, ''), webhook_url) WHERE id = ?",
            (approval_status, webhook_url, export_id),
        )
    return get_export(export_id)


def delete_generated_export(export_id: str) -> Tuple[bool, str]:
    rec = get_export(export_id)
    if not rec:
        return False, "Export non trovato."
    if rec["origin"] != "generated":
        return False, "I report ed Excel storici di repository non possono essere eliminati dall'archivio."
    fpath = resolve_stored_path(rec["file_path"])
    exports_root = get_exports_dir().resolve()
    try:
        fpath.relative_to(exports_root)
        if fpath.exists():
            fpath.unlink(missing_ok=True)
    except ValueError:
        pass
    with get_connection() as conn:
        conn.execute("DELETE FROM export_records WHERE id = ?", (export_id,))
    return True, "Export eliminato dall'archivio."


# ── OUTREACH HITL APPROVALS ─────────────────────────────────────────────────────

def list_outreach_approvals() -> Dict[str, Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM outreach_approvals").fetchall()
        return {
            r["lead_key"]: {
                "lead_key": r["lead_key"],
                "company_name": r["company_name"],
                "channel": r["channel"],
                "status": r["status"],
                "notes": r["notes"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        }


def set_outreach_approval(lead_key: str, company_name: str, channel: str, status: str, notes: str = "") -> Dict[str, Any]:
    init_db()
    now = _now_iso()
    if status not in ("PENDING", "APPROVED", "SKIPPED"):
        raise ValueError("Stato approvazione non valido.")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO outreach_approvals (lead_key, company_name, channel, status, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(lead_key) DO UPDATE SET
                company_name = excluded.company_name,
                channel = excluded.channel,
                status = excluded.status,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (lead_key, company_name, channel, status, notes, now),
        )
    return {
        "lead_key": lead_key,
        "company_name": company_name,
        "channel": channel,
        "status": status,
        "notes": notes,
        "updated_at": now,
    }
