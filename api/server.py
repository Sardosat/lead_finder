"""
server.py — API REST FastAPI per Lead Intelligence Engine IT/EU:
- Autenticazione stateless HMAC-SHA256 con cookie HttpOnly + Bearer/X-API-Key
- Gestione catalogo prodotti ecosistema (monetizelab.online, rsksystem.com, tecnicolive.it)
- Panoramica analytics, Trend Finder, Benchmark Clay (esempio.csv vs Engine)
- Le mie Ricerche (CRUD, preset multi-settore, esecuzione asincrona)
- Lead Explorer paginato/filtrato/ordinato stile Clay
- Archivio Export persistente (CSV, XLSX, WEBHOOK_JSON, PDF) + gate Human-in-the-Loop
- Outreach & Bozze 1-to-1 + Gestione Blacklist GDPR (SuppressionList)
- Connettori live VIES UE, Level 1 Tech Audit e Level 3 Openapi.com
"""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import pandas as pd
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from api.auth import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_SECONDS,
    create_session_token,
    get_auth_username,
    is_using_default_password,
    require_auth,
    verify_credentials,
)
from engine.compliance.lia_engine import SuppressionList, assess_lead_lia
from engine.connectors.openapi_italy import OpenapiItalyClient
from engine.connectors.vies_validator import ViesValidatorClient
from engine.enrichment.pipeline_runner import EnrichmentPipelineRunner
from engine.enrichment.tech_audit import TechAuditor
from engine.intelligence.market_radar import MarketRadarService
from engine.routing.product_router import PRODUCT_CATALOG, route_lead_to_product
from engine.schemas.campaign import CampaignConfig, EnrichmentLevels, GeoFilter, UpsellProduct
from engine.schemas.lead import LeadRecord
from engine.storage import (
    bootstrap_workspace_records,
    create_custom_search,
    create_export_from_leads,
    delete_custom_search,
    delete_generated_export,
    duplicate_search,
    get_export,
    get_exports_dir,
    get_search,
    get_suppression_csv_path,
    list_exports,
    list_outreach_approvals,
    list_searches,
    load_search_leads,
    resolve_stored_path,
    save_search_run_leads,
    set_outreach_approval,
    update_export_approval,
    update_search_run_state,
)
from src.config import (
    ANNUAL_DISCOUNT_PCT,
    CNA_FIRST_YEAR_DISCOUNT_PCT,
    GDPR_OPTOUT_TEXT,
    PRICING_PLANS,
    ROOT_DIR,
    SENDER_IDENTITY,
)
from src.normalizers import clean_company_website, is_mobile_e164, normalize_phone_e164

load_dotenv(ROOT_DIR / ".env", override=False)

CAMPAIGNS_DIR = ROOT_DIR / "campaigns"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    bootstrap_workspace_records()
    yield


app = FastAPI(
    title="Lead Intelligence Engine IT/EU API",
    description="Piattaforma B2B modulare stile Clay adattata al mercato italiano ed europeo.",
    version="2.0.0",
    lifespan=lifespan,
)

_cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
_cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── SCHEMI RICHIESTE ─────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class RouteRequest(BaseModel):
    company_name: str
    category: str = ""
    niche: str = ""
    ateco_code: str = ""
    website_text: str = ""
    override_product: Optional[UpsellProduct] = None


class LIARequest(BaseModel):
    company_name: str
    vat_id: str = ""
    city: str = ""
    category: str = ""
    phone: str = ""
    email: str = ""
    website: str = ""
    campaign_purpose: str = "Proposta commerciale B2B pertinente"
    has_optout_clause: bool = True


class ViesRequest(BaseModel):
    vat_id: str
    default_country: str = "IT"


class TechAuditRequest(BaseModel):
    website: str
    check_mx: bool = True


class OpenapiRequest(BaseModel):
    vat_or_cf: str
    endpoint: str = "IT-start"
    max_budget_eur: float = Field(default=1.0, ge=0.0, le=50.0)


class CreateSearchRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    target_vertical: str = Field(..., min_length=2, max_length=160)
    ateco_codes: List[str] = Field(default_factory=list)
    search_queries: List[str] = Field(default_factory=list)
    geo: GeoFilter = Field(default_factory=GeoFilter)
    product_target: UpsellProduct = "rsksystem"
    offer_summary: str = "Proposta B2B su misura"
    enrichment: EnrichmentLevels = Field(default_factory=EnrichmentLevels)
    max_results_per_query: int = Field(default=20, ge=5, le=50)
    run_now: bool = False


class GenerateExportRequest(BaseModel):
    search_id: str = "ds-outbound-tecnicolive"
    format: str = Field(default="CSV", pattern="^(CSV|XLSX|WEBHOOK_JSON)$")
    lead_ids: Optional[List[str]] = None
    view: str = "all"
    q: str = ""
    product: str = ""
    tier: str = ""
    city: str = ""
    niche: str = ""
    lia_status: str = ""
    callable_only: bool = False
    has_email: bool = False
    has_valid_piva: bool = False
    filename_prefix: str = ""


class ApproveExportRequest(BaseModel):
    human_approved: bool = False
    dispatch_webhook: bool = False
    webhook_url: Optional[str] = None


class OutreachApprovalRequest(BaseModel):
    lead_key: str
    company_name: str = ""
    channel: str = "whatsapp"
    status: str = Field(..., pattern="^(PENDING|APPROVED|SKIPPED)$")
    notes: str = ""


class SuppressionEntryRequest(BaseModel):
    phone_e164: str = ""
    email: str = ""
    vat_id: str = ""
    reason: str = "CANCELLAMI"


# ── HELPER FILTRI LEAD CONDIVISO TRA EXPLORER & EXPORT ────────────────────────────

def _filter_leads(
    leads: List[Dict[str, Any]],
    view: str = "all",
    q: str = "",
    product: str = "",
    tier: str = "",
    city: str = "",
    niche: str = "",
    cna_status: str = "",
    lia_status: str = "",
    callable_only: bool = False,
    has_email: bool = False,
    has_valid_piva: bool = False,
) -> List[Dict[str, Any]]:
    res = leads
    if view == "callable_ab":
        res = [x for x in res if x["callable"] and x["tier_code"] in ("A", "B")]
    elif view == "to_enrich":
        res = [x for x in res if not x["callable"]]
    elif view in ("tecnicolive", "rsksystem", "monetizelab"):
        res = [x for x in res if x["recommended_product"] == view]

    if product:
        res = [x for x in res if x["recommended_product"] == product.lower()]
    if tier:
        t = tier.strip().upper().replace("TIER ", "")
        res = [x for x in res if x["tier_code"] == t]
    if city:
        c_low = city.strip().lower()
        res = [x for x in res if x["city"].lower() == c_low]
    if niche:
        n_low = niche.strip().lower()
        res = [x for x in res if x["niche"].lower() == n_low]
    if cna_status:
        cs_low = cna_status.strip().lower()
        res = [x for x in res if cs_low in x["cna_status"].lower()]
    if lia_status:
        ls_up = lia_status.strip().upper()
        res = [x for x in res if x["lia_status"] == ls_up]
    if callable_only:
        res = [x for x in res if x["callable"]]
    if has_email:
        res = [x for x in res if bool(x["email"])]
    if has_valid_piva:
        res = [x for x in res if x["has_valid_piva"]]
    if q:
        q_low = q.strip().lower()
        res = [
            x
            for x in res
            if (
                q_low in x["company_name"].lower()
                or q_low in x["vat_id"].lower()
                or q_low in x["phone_e164"].lower()
                or q_low in x["city"].lower()
                or q_low in x["niche"].lower()
                or q_low in x["email"].lower()
                or any(q_low in b.lower() for b in x["brands"])
            )
        ]
    return res


def _match_local_verified_seeds(search: Dict[str, Any]) -> List[LeadRecord]:
    """
    Fallback Zero Hallucination quando mancano SERPER_API_KEY / GOOGLE_PLACES_API_KEY:
    seleziona solo aziende reali già verificate dall'archivio master locale coerenti con città/verticale.
    """
    master_leads = load_search_leads("ds-master-clean")
    if not master_leads:
        master_leads = load_search_leads("ds-outbound-tecnicolive")

    geo = search.get("geo") or {}
    munis = [m.lower() for m in (geo.get("municipalities") or []) if m]
    terms = [t.lower() for t in (search.get("target_vertical", "").split() + (search.get("search_queries") or [])) if len(t) >= 3]

    matched: List[LeadRecord] = []
    for item in master_leads:
        city_ok = True if not munis else any(m in item["city"].lower() or m in item["address"].lower() for m in munis)
        haystack = f"{item['company_name']} {item['niche']} {item['category']} {' '.join(item['brands'])}".lower()
        term_ok = True if not terms else any(t in haystack for t in terms)
        if city_ok and term_ok:
            matched.append(
                LeadRecord(
                    company_name=item["company_name"],
                    vat_id=item["vat_id"],
                    country_code=item["country_code"] or "IT",
                    province=item["province"] or "CT",
                    city=item["city"],
                    address=item["address"],
                    phone_e164=item["phone_e164"],
                    phone_secondary=item["phone_secondary"],
                    phone_type=item["phone_type"] if item["phone_type"] in ("Mobile", "Fisso") else "Unknown",
                    email=item["email"],
                    pec=item["pec"],
                    website=item["website"],
                    source="local_verified_archive",
                    category=item["category"],
                    niche=search.get("target_vertical") or item["niche"],
                )
            )
            if len(matched) >= 25:
                break
    return matched


async def _run_search_background(search_id: str) -> None:
    search = get_search(search_id)
    if not search:
        return
    try:
        geo = GeoFilter(**(search.get("geo") or {}))
        enrichment_cfg = dict(search.get("enrichment") or {})
        enrichment = EnrichmentLevels(**enrichment_cfg)
        campaign = CampaignConfig(
            campaign_id=search["id"],
            name=search["name"],
            target_vertical=search["target_vertical"] or "PMI B2B",
            ateco_codes=search.get("ateco_codes") or [],
            search_queries=search.get("search_queries") or [],
            geo=geo,
            default_upsell_product=search.get("product_target") or None,
            offer_summary=search.get("offer_summary") or "Proposta B2B",
            enrichment=enrichment,
            max_results_per_query=20,
        )

        runner = EnrichmentPipelineRunner(suppression=SuppressionList(csv_path=get_suppression_csv_path()))
        has_places_key = bool(runner.places.serper_api_key or runner.places.google_places_key)

        seed_leads: Optional[List[LeadRecord]] = None
        note = ""
        if not has_places_key:
            seed_leads = _match_local_verified_seeds(search)
            note = (
                f"Completata su archivio locale verificato ({len(seed_leads)} match reali; "
                f"imposta SERPER_API_KEY o GOOGLE_PLACES_API_KEY per discovery live)"
            )
            if not seed_leads:
                save_search_run_leads(search_id, [], cost_eur=0.0, note=note)
                return

        res = await runner.run_campaign(campaign, seed_leads=seed_leads)
        leads_out: List[LeadRecord] = res.get("leads") or []
        total_cost = float(res.get("total_cost_eur") or 0.0)
        final_note = note or f"Pipeline completata: {len(leads_out)} aziende qualificate (COSTO €{total_cost:.2f})"
        save_search_run_leads(search_id, leads_out, cost_eur=total_cost, note=final_note)
    except Exception as exc:
        update_search_run_state(search_id, status="failed", status_note=f"Errore pipeline: {exc}")


# ── ENDPOINT PUBBLICI & AUTH ─────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "lead-intelligence-engine-it-eu", "version": "2.0.0"}


@app.post("/auth/login")
async def auth_login(req: LoginRequest, response: Response):
    if not verify_credentials(req.username, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide.",
        )
    token, expires_at = create_session_token(req.username.strip())
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )
    return {
        "authenticated": True,
        "username": get_auth_username(),
        "token": token,
        "expires_at": expires_at,
        "using_default_password": is_using_default_password(),
    }


@app.post("/auth/logout")
async def auth_logout(response: Response):
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"authenticated": False}


@app.get("/auth/me")
async def auth_me(user: Dict[str, Any] = Depends(require_auth)):
    return {
        "authenticated": True,
        "username": user.get("sub"),
        "using_default_password": is_using_default_password(),
    }


# ── CATALOGO PRODOTTI, ROUTING, CONNETTORI LIVE ──────────────────────────────────

@app.get("/products")
async def list_products(_user: Dict[str, Any] = Depends(require_auth)):
    return {"products": list(PRODUCT_CATALOG.values())}


@app.get("/campaigns/presets")
async def list_campaign_presets(_user: Dict[str, Any] = Depends(require_auth)):
    presets: List[dict] = []
    if CAMPAIGNS_DIR.exists():
        for p in sorted(CAMPAIGNS_DIR.glob("*.json")):
            try:
                presets.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                continue
    return {"presets": presets}


@app.post("/routing/classify")
async def classify_product(req: RouteRequest, _user: Dict[str, Any] = Depends(require_auth)):
    return route_lead_to_product(
        company_name=req.company_name,
        category=req.category,
        niche=req.niche,
        ateco_code=req.ateco_code,
        website_text=req.website_text,
        override_product=req.override_product,
    )


@app.post("/compliance/lia")
async def evaluate_lia(req: LIARequest, _user: Dict[str, Any] = Depends(require_auth)):
    p1, p2 = normalize_phone_e164(req.phone)
    lead = LeadRecord(
        company_name=req.company_name,
        vat_id=req.vat_id,
        city=req.city,
        category=req.category,
        phone_e164=p1,
        phone_secondary=p2,
        phone_type="Mobile" if is_mobile_e164(p1) else ("Fisso" if p1 else "Unknown"),
        email=(req.email or "").strip().lower(),
        website=clean_company_website(req.website),
    )
    sup = SuppressionList(csv_path=get_suppression_csv_path())
    assessment = assess_lead_lia(
        lead=lead,
        campaign_purpose=req.campaign_purpose,
        has_optout_clause=req.has_optout_clause,
        suppression=sup,
    )
    return {
        "assessment": assessment.model_dump(),
        "sanitized_outbound_email": lead.email,
        "isolated_pec": lead.pec,
        "normalized_phone_e164": lead.phone_e164,
    }


@app.post("/enrich/vies")
async def enrich_vies(req: ViesRequest, _user: Dict[str, Any] = Depends(require_auth)):
    client = ViesValidatorClient()
    return await client.check_vat(req.vat_id, default_country=req.default_country)


@app.post("/enrich/tech-audit")
async def enrich_tech_audit(req: TechAuditRequest, _user: Dict[str, Any] = Depends(require_auth)):
    auditor = TechAuditor()
    res = await auditor.audit_website(req.website, check_mx=req.check_mx)
    return res.model_dump()


@app.post("/enrich/openapi")
async def enrich_openapi(req: OpenapiRequest, _user: Dict[str, Any] = Depends(require_auth)):
    client = OpenapiItalyClient(max_budget_eur=req.max_budget_eur)
    return await client.query_company(req.vat_or_cf, endpoint=req.endpoint)


# ── ANALYTICS, GRAFICI & TREND FINDER ────────────────────────────────────────────

@app.get("/analytics/overview")
async def analytics_overview(
    search_id: str = Query(default="ds-master-clean"),
    _user: Dict[str, Any] = Depends(require_auth),
):
    bootstrap_workspace_records()
    leads = load_search_leads(search_id)
    if not leads and search_id != "ds-outbound-tecnicolive":
        fallback = get_search(search_id)
        if not fallback:
            leads = load_search_leads("ds-master-clean")
            search_id = "ds-master-clean"

    total = len(leads)
    callable_cnt = sum(1 for x in leads if x["callable"])
    valid_piva_cnt = sum(1 for x in leads if x["has_valid_piva"])
    tier_a_cnt = sum(1 for x in leads if x["tier_code"] == "A")
    tier_b_cnt = sum(1 for x in leads if x["tier_code"] == "B")
    tier_ab_cnt = tier_a_cnt + tier_b_cnt
    lia_pass_cnt = sum(1 for x in leads if x["lia_status"] == "PASS")
    lia_rev_cnt = sum(1 for x in leads if x["lia_status"] == "REVIEW_REQUIRED")
    lia_blk_cnt = sum(1 for x in leads if x["lia_status"] == "BLOCKED")
    cna_elig_cnt = sum(1 for x in leads if x["cna_eligible_50"])
    avg_icp = round(sum(x["icp_score"] for x in leads) / total, 1) if total else 0.0

    searches_all = list_searches()
    exports_all = list_exports()

    quality_funnel = [
        {"stage": "Anagrafiche in Vista", "count": total, "pct": 100.0 if total else 0.0},
        {"stage": "Geo-Lock IT / Provincia Verified", "count": total, "pct": 100.0 if total else 0.0},
        {
            "stage": "P.IVA Luhn / Fiscale Valida",
            "count": valid_piva_cnt,
            "pct": round(valid_piva_cnt / total * 100, 1) if total else 0.0,
        },
        {
            "stage": "Telefoni Chiamabili E.164",
            "count": callable_cnt,
            "pct": round(callable_cnt / total * 100, 1) if total else 0.0,
        },
        {
            "stage": "Pronti Outbound (LIA Pass)",
            "count": lia_pass_cnt,
            "pct": round(lia_pass_cnt / total * 100, 1) if total else 0.0,
        },
    ]

    product_tier_matrix = []
    for pkey in ("tecnicolive", "rsksystem", "monetizelab"):
        p_leads = [x for x in leads if x["recommended_product"] == pkey]
        product_tier_matrix.append(
            {
                "product_key": pkey,
                "product_name": PRODUCT_CATALOG[pkey]["name"],
                "tier_a": sum(1 for x in p_leads if x["tier_code"] == "A"),
                "tier_b": sum(1 for x in p_leads if x["tier_code"] == "B"),
                "tier_c": sum(1 for x in p_leads if x["tier_code"] == "C"),
                "total": len(p_leads),
            }
        )

    city_stats: Dict[str, Dict[str, int]] = {}
    niche_stats: Dict[str, Dict[str, int]] = {}
    for x in leads:
        c = x["city"] or "Non specificato"
        cs = city_stats.setdefault(c, {"total": 0, "callable": 0, "to_enrich": 0})
        cs["total"] += 1
        if x["callable"]:
            cs["callable"] += 1
        else:
            cs["to_enrich"] += 1

        n = x["niche"] or "Altro"
        ns = niche_stats.setdefault(n, {"total": 0, "callable": 0, "to_enrich": 0})
        ns["total"] += 1
        if x["callable"]:
            ns["callable"] += 1
        else:
            ns["to_enrich"] += 1

    geo_coverage = [
        {"label": k, **v}
        for k, v in sorted(city_stats.items(), key=lambda kv: kv[1]["total"], reverse=True)[:10]
    ]
    niche_coverage = [
        {"label": k, **v}
        for k, v in sorted(niche_stats.items(), key=lambda kv: kv[1]["total"], reverse=True)[:8]
    ]

    return {
        "search_id": search_id,
        "kpis": {
            "total_leads": total,
            "callable_e164": callable_cnt,
            "valid_piva": valid_piva_cnt,
            "tier_a": tier_a_cnt,
            "tier_a_b": tier_ab_cnt,
            "avg_icp_score": avg_icp,
            "lia_pass": lia_pass_cnt,
            "lia_review": lia_rev_cnt,
            "lia_blocked": lia_blk_cnt,
            "cna_eligible": cna_elig_cnt,
            "exports_count": len(exports_all),
            "searches_count": len(searches_all),
        },
        "quality_funnel": quality_funnel,
        "product_tier_matrix": product_tier_matrix,
        "geo_coverage": geo_coverage,
        "niche_coverage": niche_coverage,
        "recent_searches": searches_all[:5],
        "recent_exports": exports_all[:5],
    }


@app.get("/analytics/clay-benchmark")
async def analytics_clay_benchmark(_user: Dict[str, Any] = Depends(require_auth)):
    clay_path = ROOT_DIR / "esempio.csv"
    master_leads = load_search_leads("ds-master-clean")
    outbound_leads = load_search_leads("ds-outbound-tecnicolive")

    clay_rows = 0
    clay_non_it: List[Dict[str, str]] = []
    clay_phone_cols = 0
    clay_email_cols = 0
    clay_piva_cols = 0

    if clay_path.exists():
        with open(clay_path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            clay_phone_cols = sum(1 for c in cols if "phone" in c.lower() or "tel" in c.lower())
            clay_email_cols = sum(1 for c in cols if "email" in c.lower() or "mail" in c.lower())
            clay_piva_cols = sum(1 for c in cols if "piva" in c.lower() or "vat" in c.lower())
            for row in reader:
                clay_rows += 1
                country = (row.get("Country") or "").strip()
                if country and country.lower() != "italy":
                    clay_non_it.append(
                        {
                            "name": row.get("Name") or "",
                            "domain": row.get("Domain") or "",
                            "city": row.get("City") or "",
                            "state": row.get("State or Province") or "",
                            "country": country,
                            "size": row.get("Size") or "",
                        }
                    )

    clay_italy_cnt = max(0, clay_rows - len(clay_non_it))
    clay_italy_pct = round((clay_italy_cnt / clay_rows) * 100, 1) if clay_rows else 0.0

    m_total = len(master_leads)
    m_piva = sum(1 for x in master_leads if x["has_valid_piva"])
    m_call = sum(1 for x in master_leads if x["callable"])
    m_email = sum(1 for x in master_leads if x["email"])

    comparison_bars = [
        {
            "metric": "Precisione Geografica Italia (%)",
            "clay": clay_italy_pct,
            "engine": 100.0 if m_total else 0.0,
        },
        {
            "metric": "Copertura Telefoni E.164 (%)",
            "clay": 0.0,
            "engine": round((m_call / m_total) * 100, 1) if m_total else 0.0,
        },
        {
            "metric": "P.IVA Validate Luhn (%)",
            "clay": 0.0,
            "engine": round((m_piva / m_total) * 100, 1) if m_total else 0.0,
        },
        {
            "metric": "Email Ordinarie (No PEC) (%)",
            "clay": 0.0,
            "engine": round((m_email / m_total) * 100, 1) if m_total else 0.0,
        },
    ]

    return {
        "clay_summary": {
            "source_file": "esempio.csv",
            "total_rows": clay_rows,
            "non_italy_count": len(clay_non_it),
            "italy_accuracy_pct": clay_italy_pct,
            "phone_columns": clay_phone_cols,
            "email_columns": clay_email_cols,
            "piva_columns": clay_piva_cols,
            "non_italy_examples": clay_non_it,
        },
        "engine_summary": {
            "master_total": m_total,
            "outbound_callable": len(outbound_leads),
            "valid_piva_count": m_piva,
            "ordinary_emails_count": m_email,
            "italy_accuracy_pct": 100.0 if m_total else 0.0,
            "pec_cold_block": True,
        },
        "comparison_bars": comparison_bars,
    }


@app.get("/analytics/trends")
async def analytics_trends(
    search_id: str = Query(default="ds-master-clean"),
    _user: Dict[str, Any] = Depends(require_auth),
):
    leads = load_search_leads(search_id)
    total = len(leads)

    office_hours_no_h24 = sum(1 for x in leads if not x["is_h24"])
    cna_non_associated = sum(1 for x in leads if x["cna_eligible_50"])
    verified_brand_specialists = sum(1 for x in leads if x["brands_verified"])
    to_enrich_no_phone = sum(1 for x in leads if not x["callable"])
    with_website = sum(1 for x in leads if x["website"])

    trigger_counter: Counter[str] = Counter()
    brand_counter: Counter[str] = Counter()
    for x in leads:
        if x["trigger_signal"]:
            trigger_counter[x["trigger_signal"]] += 1
        for b in x["brands"]:
            brand_counter[b] += 1

    # Curva stagionale esplicitamente marcata STIMA TEORICA / MODELLO PREDITTIVO (AGENTS.md §2)
    seasonality_12m = [
        {"month": "Gen", "climatizzazione": 22, "caldaie_termoidraulica": 92, "manutenzione_pdc": 42},
        {"month": "Feb", "climatizzazione": 25, "caldaie_termoidraulica": 84, "manutenzione_pdc": 48},
        {"month": "Mar", "climatizzazione": 36, "caldaie_termoidraulica": 62, "manutenzione_pdc": 65},
        {"month": "Apr", "climatizzazione": 54, "caldaie_termoidraulica": 40, "manutenzione_pdc": 72},
        {"month": "Mag", "climatizzazione": 78, "caldaie_termoidraulica": 28, "manutenzione_pdc": 68},
        {"month": "Giu", "climatizzazione": 95, "caldaie_termoidraulica": 20, "manutenzione_pdc": 50},
        {"month": "Lug", "climatizzazione": 100, "caldaie_termoidraulica": 18, "manutenzione_pdc": 40},
        {"month": "Ago", "climatizzazione": 92, "caldaie_termoidraulica": 16, "manutenzione_pdc": 35},
        {"month": "Set", "climatizzazione": 74, "caldaie_termoidraulica": 35, "manutenzione_pdc": 66},
        {"month": "Ott", "climatizzazione": 42, "caldaie_termoidraulica": 72, "manutenzione_pdc": 74},
        {"month": "Nov", "climatizzazione": 28, "caldaie_termoidraulica": 88, "manutenzione_pdc": 55},
        {"month": "Dic", "climatizzazione": 24, "caldaie_termoidraulica": 96, "manutenzione_pdc": 45},
    ]

    regulatory_drivers = [
        {
            "id": "cna-50",
            "title": "Convenzione CNA Catania — Quota Associativa al 50% (1° Anno)",
            "badge": "LEVA COMMERCIALE ATTIVA",
            "summary": (
                "Le imprese non ancora associate accedono all'associazione CNA Catania al 50% della quota "
                "per tutto il primo anno insieme all'attivazione di TecnicoLIVE."
            ),
            "target_count": cna_non_associated,
        },
        {
            "id": "citel",
            "title": "Catasto Impianti Termici Sicilia (CITEL) & Bollino Blu",
            "badge": "NORMATIVO",
            "summary": (
                "Obbligo di caricamento telematico dei rapporti di efficienza energetica in Sicilia. "
                "Il centralino vocale AI raccoglie matricola e dati impianto già in chiamata."
            ),
            "target_count": sum(1 for x in leads if "CITEL" in " ".join(x["certifications"]).upper() or "calda" in x["niche"].lower() or "termo" in x["niche"].lower()),
        },
        {
            "id": "fgas-dm37",
            "title": "Patentino F-Gas & Dichiarazioni di Conformità DM 37/08",
            "badge": "QUALIFICAZIONE",
            "summary": (
                "Corsi, aggiornamenti normativi e tutela tecnica tramite CNA Catania; alto valore per imprese "
                "climatizzazione e impianti elettrici."
            ),
            "target_count": sum(1 for x in leads if "F-Gas" in x["certifications"] or "DM 37/08" in x["certifications"]),
        },
        {
            "id": "pdc-transizione",
            "title": "Transizione Energetica & Pompe di Calore",
            "badge": "DOMANDA INTERVENTI",
            "summary": (
                "Preventivi ad alto ticket medio: chi risponde entro 3 secondi con chiamate simultanee "
                "illimitate acquisisce il sopralluogo prima dei competitor."
            ),
            "target_count": with_website,
        },
    ]

    keyword_clusters = [
        {
            "cluster": "Riscaldamento & Caldaie",
            "keywords": [
                "assistenza caldaie catania h24",
                "blocco caldaia vaillant acireale",
                "costo bollino blu caldaia catania",
                "tecnico caldaie ariston catania",
            ],
        },
        {
            "cluster": "Climatizzazione & HVAC",
            "keywords": [
                "ricarica condizionatore catania subito",
                "installazione climatizzatori acireale",
                "condizionatore non raffredda misterbianco",
                "preventivo dual split catania",
            ],
        },
        {
            "cluster": "Idraulica & Elettrico Urgenze",
            "keywords": [
                "idraulico pronto intervento catania",
                "riparazione perdita acqua acireale",
                "elettricista urgente catania h24",
                "certificazione conformità impianto 37/08",
            ],
        },
        {
            "cluster": "Agenzie, Creator & PMI (MonetizeLab / RSK)",
            "keywords": [
                "agenzia marketing digitale catania",
                "automazione whatsapp crm pmi sicilia",
                "lead generation b2b italia gdpr",
                "web agency palermo milano roma",
            ],
        },
    ]

    return {
        "search_id": search_id,
        "disclaimer": (
            "STIMA TEORICA / MODELLO PREDITTIVO (AGENTS.md §2): gli indici stagionali 12 mesi (0–100) "
            "sono stime operative di calendario; i contatori dei segnali e marchi sottostanti sono reali sull'archivio selezionato."
        ),
        "seasonality_12m": seasonality_12m,
        "real_intent_signals": {
            "total_analyzed": total,
            "office_hours_no_h24": office_hours_no_h24,
            "cna_non_associated": cna_non_associated,
            "verified_brand_specialists": verified_brand_specialists,
            "to_enrich_no_phone": to_enrich_no_phone,
            "with_website": with_website,
            "trigger_breakdown": [
                {"trigger": k, "count": v} for k, v in trigger_counter.most_common(6)
            ],
            "top_brands": [{"brand": k, "count": v} for k, v in brand_counter.most_common(10)],
        },
        "regulatory_drivers": regulatory_drivers,
        "keyword_clusters": keyword_clusters,
    }


# ── LE MIE RICERCHE (CRUD + ESECUZIONE) ──────────────────────────────────────────

@app.get("/searches")
async def api_list_searches(_user: Dict[str, Any] = Depends(require_auth)):
    return {"searches": list_searches()}


@app.get("/searches/{search_id}")
async def api_get_search(search_id: str, _user: Dict[str, Any] = Depends(require_auth)):
    item = get_search(search_id)
    if not item:
        raise HTTPException(status_code=404, detail="Ricerca non trovata.")
    return item


@app.post("/searches")
async def api_create_search(
    req: CreateSearchRequest,
    background_tasks: BackgroundTasks,
    _user: Dict[str, Any] = Depends(require_auth),
):
    created = create_custom_search(
        {
            "name": req.name,
            "target_vertical": req.target_vertical,
            "ateco_codes": req.ateco_codes,
            "search_queries": req.search_queries,
            "geo": req.geo.model_dump(),
            "product_target": req.product_target,
            "offer_summary": req.offer_summary,
            "enrichment": req.enrichment.model_dump(),
            "max_results_per_query": req.max_results_per_query,
            "run_now": req.run_now,
        }
    )
    if req.run_now and created.get("id"):
        background_tasks.add_task(_run_search_background, created["id"])
    return created


@app.post("/searches/{search_id}/run")
async def api_run_search(
    search_id: str,
    background_tasks: BackgroundTasks,
    _user: Dict[str, Any] = Depends(require_auth),
):
    item = get_search(search_id)
    if not item:
        raise HTTPException(status_code=404, detail="Ricerca non trovata.")
    update_search_run_state(search_id, status="running", status_note="Pipeline avviata in background...")
    background_tasks.add_task(_run_search_background, search_id)
    return get_search(search_id)


@app.post("/searches/{search_id}/duplicate")
async def api_duplicate_search(search_id: str, _user: Dict[str, Any] = Depends(require_auth)):
    dup = duplicate_search(search_id)
    if not dup:
        raise HTTPException(status_code=404, detail="Ricerca da duplicare non trovata.")
    return dup


@app.delete("/searches/{search_id}")
async def api_delete_search(search_id: str, _user: Dict[str, Any] = Depends(require_auth)):
    ok, msg = delete_custom_search(search_id)
    if not ok:
        raise HTTPException(status_code=400 if "archivi" in msg.lower() else 404, detail=msg)
    return {"deleted": True, "id": search_id, "message": msg}


# ── LEAD EXPLORER (TABELLA INTELLIGENTE) ─────────────────────────────────────────

@app.get("/leads")
async def api_list_leads(
    search_id: str = Query(default="ds-outbound-tecnicolive"),
    view: str = Query(default="all"),
    q: str = Query(default=""),
    product: str = Query(default=""),
    tier: str = Query(default=""),
    city: str = Query(default=""),
    niche: str = Query(default=""),
    cna_status: str = Query(default=""),
    lia_status: str = Query(default=""),
    callable_only: bool = Query(default=False),
    has_email: bool = Query(default=False),
    has_valid_piva: bool = Query(default=False),
    sort_by: str = Query(default="icp_score"),
    sort_dir: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    _user: Dict[str, Any] = Depends(require_auth),
):
    leads = load_search_leads(search_id)
    filtered = _filter_leads(
        leads=leads,
        view=view,
        q=q,
        product=product,
        tier=tier,
        city=city,
        niche=niche,
        cna_status=cna_status,
        lia_status=lia_status,
        callable_only=callable_only,
        has_email=has_email,
        has_valid_piva=has_valid_piva,
    )

    reverse = sort_dir.lower() != "asc"
    valid_sort_keys = {
        "company_name",
        "city",
        "niche",
        "icp_score",
        "tier_code",
        "recommended_product",
        "lia_status",
        "vat_id",
        "phone_e164",
    }
    sk = sort_by if sort_by in valid_sort_keys else "icp_score"
    filtered = sorted(
        filtered,
        key=lambda x: (x.get(sk) if isinstance(x.get(sk), (int, float)) else str(x.get(sk) or "").lower()),
        reverse=reverse,
    )

    total = len(filtered)
    total_pages = max(1, (total + page_size - 1) // page_size)
    safe_page = min(page, total_pages)
    start = (safe_page - 1) * page_size
    items = filtered[start : start + page_size]

    pain_counter: Counter[str] = Counter()
    pain_meta: Dict[str, Dict[str, str]] = {}
    weak_counter: Counter[str] = Counter()
    weak_meta: Dict[str, str] = {}
    strength_counter: Counter[str] = Counter()
    strength_meta: Dict[str, str] = {}
    prod_counter: Counter[str] = Counter()
    size_counter: Counter[str] = Counter()

    for x in filtered:
        for p in x.get("pain_signals") or []:
            t = p.get("title") or ""
            if t:
                pain_counter[t] += 1
                pain_meta.setdefault(t, {"category": p.get("category", ""), "attack_angle": p.get("attack_angle", "")})
        for w in x.get("weak_points") or []:
            t = w.get("title") or ""
            if t:
                weak_counter[t] += 1
                weak_meta.setdefault(t, w.get("category", ""))
        for s in x.get("strengths") or []:
            t = s.get("title") or ""
            if t:
                strength_counter[t] += 1
                strength_meta.setdefault(t, s.get("category", ""))
        prod_key = x.get("recommended_product") or "rsksystem"
        prod_counter[prod_key] += 1
        sz = x.get("company_size_label") or "Ditta Individuale / Artigiano"
        size_counter[sz] += 1

    return {
        "search_id": search_id,
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": page_size,
        "total_pages": total_pages,
        "summary": {
            "dataset_total": len(leads),
            "filtered_callable": sum(1 for x in filtered if x["callable"]),
            "filtered_valid_piva": sum(1 for x in filtered if x["has_valid_piva"]),
            "filtered_tier_ab": sum(1 for x in filtered if x["tier_code"] in ("A", "B")),
            "filtered_lia_pass": sum(1 for x in filtered if x["lia_status"] == "PASS"),
        },
        "insights": {
            "top_pain_points": [
                {"title": k, "count": v, **pain_meta.get(k, {})}
                for k, v in pain_counter.most_common(8)
            ],
            "top_weak_points": [
                {"title": k, "count": v, "category": weak_meta.get(k, "")}
                for k, v in weak_counter.most_common(8)
            ],
            "top_strengths": [
                {"title": k, "count": v, "category": strength_meta.get(k, "")}
                for k, v in strength_counter.most_common(8)
            ],
            "product_breakdown": [
                {
                    "product_key": k,
                    "product_name": PRODUCT_CATALOG.get(k, PRODUCT_CATALOG["rsksystem"])["name"],
                    "count": v,
                }
                for k, v in prod_counter.most_common()
            ],
            "size_breakdown": [{"label": k, "count": v} for k, v in size_counter.most_common()],
            "avg_pain_per_lead": round(sum(len(x.get("pain_signals") or []) for x in filtered) / total, 1) if total else 0.0,
            "avg_weak_per_lead": round(sum(len(x.get("weak_points") or []) for x in filtered) / total, 1) if total else 0.0,
            "avg_strength_per_lead": round(sum(len(x.get("strengths") or []) for x in filtered) / total, 1) if total else 0.0,
        },
    }


@app.get("/leads/facets")
async def api_lead_facets(
    search_id: str = Query(default="ds-outbound-tecnicolive"),
    _user: Dict[str, Any] = Depends(require_auth),
):
    leads = load_search_leads(search_id)
    cities = Counter(x["city"] for x in leads if x["city"])
    niches = Counter(x["niche"] for x in leads if x["niche"])
    products = Counter(x["recommended_product"] for x in leads)
    tiers = Counter(x["tier_code"] for x in leads)
    lia = Counter(x["lia_status"] for x in leads)
    cna = Counter(x["cna_status"] for x in leads if x["cna_status"])

    return {
        "cities": [{"value": k, "count": v} for k, v in cities.most_common()],
        "niches": [{"value": k, "count": v} for k, v in niches.most_common()],
        "products": [{"value": k, "count": v} for k, v in products.most_common()],
        "tiers": [{"value": k, "count": v} for k, v in sorted(tiers.items())],
        "lia_statuses": [{"value": k, "count": v} for k, v in lia.most_common()],
        "cna_statuses": [{"value": k, "count": v} for k, v in cna.most_common()],
    }


# ── ARCHIVIO EXPORT (SALVATAGGIO, ANTEPRIMA, DOWNLOAD, HITL) ─────────────────────

@app.get("/exports")
async def api_list_exports(
    format: str = Query(default=""),
    search_id: str = Query(default=""),
    approval_status: str = Query(default=""),
    _user: Dict[str, Any] = Depends(require_auth),
):
    records = list_exports(fmt=format, search_id=search_id, approval_status=approval_status)
    all_records = list_exports()
    by_format = Counter(r["format"] for r in all_records)
    return {
        "exports": records,
        "counts": {
            "total": len(all_records),
            "csv_xlsx": by_format["CSV"] + by_format["XLSX"],
            "webhook_json": by_format["WEBHOOK_JSON"],
            "pdf": by_format["PDF"],
            "markdown": by_format["MARKDOWN"],
        },
    }


@app.post("/exports/generate")
async def api_generate_export(req: GenerateExportRequest, _user: Dict[str, Any] = Depends(require_auth)):
    search = get_search(req.search_id)
    search_name = search["name"] if search else req.search_id
    all_leads = load_search_leads(req.search_id)

    if req.lead_ids:
        id_set = set(req.lead_ids)
        candidates = [x for x in all_leads if x["id"] in id_set]
    else:
        candidates = _filter_leads(
            leads=all_leads,
            view=req.view,
            q=req.q,
            product=req.product,
            tier=req.tier,
            city=req.city,
            niche=req.niche,
            lia_status=req.lia_status,
            callable_only=req.callable_only,
            has_email=req.has_email,
            has_valid_piva=req.has_valid_piva,
        )

    filters_applied = {
        "view": req.view,
        "q": req.q,
        "product": req.product,
        "tier": req.tier,
        "city": req.city,
        "niche": req.niche,
        "lia_status": req.lia_status,
        "callable_only": req.callable_only,
        "has_email": req.has_email,
        "has_valid_piva": req.has_valid_piva,
        "selected_ids_count": len(req.lead_ids) if req.lead_ids else 0,
    }
    record = create_export_from_leads(
        search_id=req.search_id,
        search_name=search_name,
        fmt=req.format,
        candidate_leads=candidates,
        filters_applied=filters_applied,
        filename_prefix=req.filename_prefix,
    )
    return record


@app.get("/exports/{export_id}/download")
async def api_download_export(export_id: str, _user: Dict[str, Any] = Depends(require_auth)):
    rec = get_export(export_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Export non trovato.")
    fpath = resolve_stored_path(rec["file_path"])
    allowed_roots = (ROOT_DIR.resolve(), get_exports_dir().resolve())
    in_allowed_root = False
    for root in allowed_roots:
        try:
            fpath.relative_to(root)
            in_allowed_root = True
            break
        except ValueError:
            continue
    if not in_allowed_root:
        raise HTTPException(status_code=403, detail="Accesso al percorso negato.")
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="File non più presente su disco.")

    media_map = {
        "CSV": "text/csv; charset=utf-8",
        "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "WEBHOOK_JSON": "application/json; charset=utf-8",
        "PDF": "application/pdf",
        "MARKDOWN": "text/markdown; charset=utf-8",
    }
    return FileResponse(
        path=str(fpath),
        filename=rec["filename"],
        media_type=media_map.get(rec["format"], "application/octet-stream"),
    )


@app.get("/exports/{export_id}/preview")
async def api_preview_export(export_id: str, _user: Dict[str, Any] = Depends(require_auth)):
    rec = get_export(export_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Export non trovato.")
    fpath = resolve_stored_path(rec["file_path"])
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="File non trovato.")

    fmt = rec["format"]
    if fmt == "CSV":
        df = pd.read_csv(fpath, dtype=str).fillna("").head(20)
        return {"format": fmt, "columns": list(df.columns), "rows": df.to_dict(orient="records"), "record": rec}
    if fmt == "XLSX":
        df = pd.read_excel(fpath, dtype=str).fillna("").head(20)
        return {"format": fmt, "columns": list(df.columns), "rows": df.to_dict(orient="records"), "record": rec}
    if fmt == "WEBHOOK_JSON":
        data = json.loads(fpath.read_text(encoding="utf-8"))
        preview_data = dict(data)
        if isinstance(preview_data.get("contacts"), list):
            preview_data["contacts"] = preview_data["contacts"][:10]
        return {"format": fmt, "json_preview": preview_data, "record": rec}
    if fmt == "MARKDOWN":
        return {"format": fmt, "text_preview": fpath.read_text(encoding="utf-8")[:6000], "record": rec}
    return {
        "format": "PDF",
        "filename": rec["filename"],
        "size_bytes": rec["size_bytes"],
        "note": "Documento PDF pronto per download e consultazione esecutiva.",
        "record": rec,
    }


@app.post("/exports/{export_id}/approve")
async def api_approve_export(
    export_id: str,
    req: ApproveExportRequest,
    _user: Dict[str, Any] = Depends(require_auth),
):
    rec = get_export(export_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Export non trovato.")
    if not req.human_approved:
        raise HTTPException(
            status_code=400,
            detail="Conferma umana esplicita obbligatoria (AGENTS.md §1) prima di approvare o inviare.",
        )

    if req.dispatch_webhook and rec["format"] == "WEBHOOK_JSON":
        target_url = (req.webhook_url or os.getenv("RSK_WEBHOOK_URL") or "").strip()
        if not target_url:
            raise HTTPException(status_code=400, detail="Specifica un Webhook URL o imposta RSK_WEBHOOK_URL in .env.")
        fpath = resolve_stored_path(rec["file_path"])
        payload = json.loads(fpath.read_text(encoding="utf-8"))
        async with aiohttp.ClientSession() as session:
            async with session.post(target_url, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status >= 300:
                    raise HTTPException(status_code=502, detail=f"Webhook remoto ha risposto HTTP {resp.status}")
        updated = update_export_approval(export_id, "DISPATCHED", webhook_url=target_url)
        return {"record": updated, "dispatched": True}

    updated = update_export_approval(export_id, "APPROVED")
    return {"record": updated, "dispatched": False}


@app.delete("/exports/{export_id}")
async def api_delete_export(export_id: str, _user: Dict[str, Any] = Depends(require_auth)):
    ok, msg = delete_generated_export(export_id)
    if not ok:
        raise HTTPException(status_code=400 if "storici" in msg.lower() else 404, detail=msg)
    return {"deleted": True, "id": export_id, "message": msg}


# ── OUTREACH & SALES HUB ─────────────────────────────────────────────────────────

@app.get("/outreach/drafts")
async def api_outreach_drafts(
    search_id: str = Query(default="ds-outbound-tecnicolive"),
    product: str = Query(default=""),
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=15, ge=1, le=50),
    _user: Dict[str, Any] = Depends(require_auth),
):
    leads = load_search_leads(search_id)
    eligible = _filter_leads(leads, product=product, q=q)
    eligible = [x for x in eligible if x["lia_status"] != "BLOCKED" and (x["phone_e164"] or x["email"])]
    approvals = list_outreach_approvals()

    drafts = []
    for x in eligible:
        appr = approvals.get(x["lead_key"], {})
        drafts.append(
            {
                "lead_id": x["id"],
                "lead_key": x["lead_key"],
                "company_name": x["company_name"],
                "city": x["city"],
                "phone_e164": x["phone_e164"],
                "email": x["email"],
                "recommended_product": x["recommended_product"],
                "recommended_product_name": x["recommended_product_name"],
                "icp_score": x["icp_score"],
                "tier_code": x["tier_code"],
                "icebreaker_1to1": x["icebreaker_1to1"],
                "whatsapp_draft": x["whatsapp_draft"],
                "approval_status": appr.get("status", "PENDING"),
                "checks": {
                    "has_sender": SENDER_IDENTITY.split("—")[0].strip() in x["whatsapp_draft"] or "Sinergia" in x["whatsapp_draft"],
                    "has_optout": "CANCELLAMI" in x["whatsapp_draft"] and "privacy@tecnicolive.it" in x["whatsapp_draft"],
                    "no_pec_in_email": not bool(x["email"] and "pec" in x["email"]),
                    "rpo_required": x["rpo_required"],
                },
            }
        )

    total = len(drafts)
    total_pages = max(1, (total + page_size - 1) // page_size)
    safe_page = min(page, total_pages)
    start = (safe_page - 1) * page_size

    scripts = [
        {
            "id": "script-cna-associati",
            "title": "Script Telefonico — Aziende già Associate a CNA Catania",
            "body": (
                f'Operatore: "Buongiorno [Nome Titolare/Azienda], la chiamo da {SENDER_IDENTITY}. '
                "La contatto in merito alla convenzione ufficiale attiva con CNA Catania per le imprese impiantistiche. "
                "Sappiamo che mentre siete in cantiere molte chiamate di nuovi clienti finiscono senza risposta. "
                f"Con TecnicoLIVE attivate l'assistente vocale AI con chiamate simultanee illimitate che risponde H24, "
                f"fa la pre-diagnosi del guasto e vi invia la scheda intervento su WhatsApp (piani da {PRICING_PLANS['base']['monthly']}€/mese, "
                f"-{ANNUAL_DISCOUNT_PCT}% annuale). Ha 5 minuti oggi per chiamare il numero test +39 095 342 0411?\"\n\n"
                f"[Opt-Out follow-up scritto: {GDPR_OPTOUT_TEXT}]"
            ),
        },
        {
            "id": "script-cna-non-associati",
            "title": f"Script Telefonico — Aziende NON Associate (Leva CNA -{CNA_FIRST_YEAR_DISCOUNT_PCT}% 1° Anno)",
            "body": (
                f'Operatore: "Buongiorno [Nome Titolare], chiamo da {SENDER_IDENTITY}. '
                "Stiamo attivando nella zona di [Comune] la convenzione esclusiva con CNA Catania per gli impiantisti. "
                f"Poiché non risultate ancora associati, attiviamo TecnicoLIVE e sblocchiamo la vostra associazione a CNA Catania "
                f"al {CNA_FIRST_YEAR_DISCOUNT_PCT}% della quota per tutto il primo anno, con tutela legale, fiscale e supporto CITEL e F-Gas. "
                'Chi si occupa in azienda di valutare convenzioni e gestione chiamate?"\n\n'
                f"[Opt-Out follow-up scritto: {GDPR_OPTOUT_TEXT}]"
            ),
        },
    ]

    objections = [
        {
            "objection": "Risponde già mia moglie / ho già una segretaria",
            "rebuttal": "TecnicoLIVE non sostituisce la segretaria, la potenzia: chiamate simultanee illimitate quando una linea è già occupata, più copertura H24 sera, weekend e festivi.",
        },
        {
            "objection": "I clienti vogliono parlare direttamente con me",
            "rebuttal": "Quando sei sotto una caldaia o alla guida non puoi rispondere a fondo. L'assistente risponde in 3 secondi, raccoglie guasto e indirizzo e ti manda la scheda WhatsApp per richiamare già preparato.",
        },
        {
            "objection": "Costa troppo",
            "rebuttal": f"Base da {PRICING_PLANS['base']['monthly']}€/mese ({PRICING_PLANS['base']['annual_monthly']:.2f}€/m annuale -20%), Pro da {PRICING_PLANS['pro']['monthly']}€/m, più CNA al {CNA_FIRST_YEAR_DISCOUNT_PCT}% il 1° anno: basta recuperare 1–2 interventi al mese.",
        },
        {
            "objection": "L'Intelligenza Artificiale sbaglia / sembra un robot",
            "rebuttal": "Comprende il gergo tecnico ('blocco F28', 'termocoppia', CITEL) e i nomi dei comuni locali. Fai una chiamata test reale al +39 095 342 0411.",
        },
    ]

    return {
        "drafts": drafts[start : start + page_size],
        "total": total,
        "page": safe_page,
        "page_size": page_size,
        "total_pages": total_pages,
        "approved_count": sum(1 for d in drafts if d["approval_status"] == "APPROVED"),
        "pricing_plans": PRICING_PLANS,
        "annual_discount_pct": ANNUAL_DISCOUNT_PCT,
        "cna_first_year_discount_pct": CNA_FIRST_YEAR_DISCOUNT_PCT,
        "sender_identity": SENDER_IDENTITY,
        "gdpr_optout_text": GDPR_OPTOUT_TEXT,
        "scripts": scripts,
        "objections": objections,
        "products": list(PRODUCT_CATALOG.values()),
    }


@app.post("/outreach/approve")
async def api_approve_outreach(req: OutreachApprovalRequest, _user: Dict[str, Any] = Depends(require_auth)):
    return set_outreach_approval(
        lead_key=req.lead_key,
        company_name=req.company_name,
        channel=req.channel,
        status=req.status,
        notes=req.notes,
    )


# ── COMPLIANCE & SUPPRESSION LIST ────────────────────────────────────────────────

@app.get("/compliance/suppression")
async def api_list_suppression(_user: Dict[str, Any] = Depends(require_auth)):
    sup = SuppressionList(csv_path=get_suppression_csv_path())
    entries = sup.list_entries()
    return {"entries": entries, "total": len(entries)}


@app.post("/compliance/suppression")
async def api_add_suppression(req: SuppressionEntryRequest, _user: Dict[str, Any] = Depends(require_auth)):
    p1, _ = normalize_phone_e164(req.phone_e164) if req.phone_e164.strip() else ("", "")
    final_phone = p1 or req.phone_e164.strip()
    final_email = req.email.strip().lower()
    final_vat = req.vat_id.strip().upper()
    if not (final_phone or final_email or final_vat):
        raise HTTPException(status_code=400, detail="Inserisci almeno un Telefono, Email o Partita IVA da bloccare.")
    sup = SuppressionList(csv_path=get_suppression_csv_path())
    sup.add_optout(phone_e164=final_phone, email=final_email, vat_id=final_vat, reason=req.reason.strip() or "CANCELLAMI")
    return {"added": True, "entries": sup.list_entries()}


@app.delete("/compliance/suppression")
async def api_delete_suppression(
    phone_e164: str = Query(default=""),
    email: str = Query(default=""),
    vat_id: str = Query(default=""),
    _user: Dict[str, Any] = Depends(require_auth),
):
    sup = SuppressionList(csv_path=get_suppression_csv_path())
    removed = sup.remove_optout(phone_e164=phone_e164, email=email, vat_id=vat_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Voce non trovata in blacklist.")
    return {"removed": True, "entries": sup.list_entries()}


# ── IMPOSTAZIONI & STATO CONNETTORI (ZERO SECRET EXPOSURE) ───────────────────────

@app.get("/settings/status")
async def api_settings_status(user: Dict[str, Any] = Depends(require_auth)):
    openapi_env = (os.getenv("OPENAPI_ENV") or "production").strip().lower()
    return {
        "auth": {
            "username": user.get("sub") or get_auth_username(),
            "using_default_password": is_using_default_password(),
        },
        "providers": [
            {
                "key": "vies_eu",
                "name": "Commissione Europea VIES REST",
                "category": "Fiscale L1",
                "configured": True,
                "mode": "Gratuito / Attivo",
                "notes": "Validazione ufficiale Partite IVA IT/EU in tempo reale.",
            },
            {
                "key": "tech_audit",
                "name": "Crawler L1 Tech Audit + DNS MX",
                "category": "Arricchimento L1",
                "configured": True,
                "mode": "Locale / Attivo",
                "notes": "Controllo HTTP, SSL, CMS, Pixel, WhatsApp CTA, estrazione P.IVA e MX via dnspython.",
            },
            {
                "key": "openapi_italy",
                "name": "Openapi.com Registro Imprese",
                "category": "Camerale L3",
                "configured": bool(
                    (os.getenv("OPENAPI_TOKEN") or "").strip()
                    or ((os.getenv("OPENAPI_USERNAME") or "").strip() and (os.getenv("OPENAPI_API_KEY") or "").strip())
                ),
                "mode": openapi_env,
                "notes": "ATECO, stato attività, forma giuridica, PEC ufficiale, SDI e fascia bilancio con budget cap.",
            },
            {
                "key": "gemini_ai",
                "name": "Google Gemini 2.5 Flash",
                "category": "Qualificazione L2",
                "configured": bool((os.getenv("GEMINI_API_KEY") or "").strip()),
                "mode": "Structured JSON" if (os.getenv("GEMINI_API_KEY") or "").strip() else "Fallback Deterministico Attivo",
                "notes": "Estrazione pain point citati e personalizzazione outreach.",
            },
            {
                "key": "serper_places",
                "name": "Serper.dev Google Places",
                "category": "Discovery Seed",
                "configured": bool((os.getenv("SERPER_API_KEY") or "").strip()),
                "mode": "API Key configurata" if (os.getenv("SERPER_API_KEY") or "").strip() else "Non configurata (usa archivio verificato)",
                "notes": "Scoperta locale per query/città protetta da Geo-Lock ISTAT.",
            },
            {
                "key": "google_places",
                "name": "Google Places API (New)",
                "category": "Discovery Seed",
                "configured": bool((os.getenv("GOOGLE_PLACES_API_KEY") or "").strip()),
                "mode": "API Key configurata" if (os.getenv("GOOGLE_PLACES_API_KEY") or "").strip() else "Non configurata",
                "notes": "Alternativa ufficiale a Serper Places.",
            },
            {
                "key": "rsk_webhook",
                "name": "Webhook RSK System / GoHighLevel / n8n",
                "category": "Consegna HITL",
                "configured": bool((os.getenv("RSK_WEBHOOK_URL") or "").strip()),
                "mode": "Conferma Umana Obbligatoria",
                "notes": "Invio bloccato di default finché l'utente non approva in Archivio Export.",
            },
        ],
        "sender_identity": SENDER_IDENTITY,
        "gdpr_optout_text": GDPR_OPTOUT_TEXT,
        "pricing_plans": PRICING_PLANS,
        "annual_discount_pct": ANNUAL_DISCOUNT_PCT,
        "cna_first_year_discount_pct": CNA_FIRST_YEAR_DISCOUNT_PCT,
        "products": list(PRODUCT_CATALOG.values()),
    }


# ── SOCIAL & MARKET RADAR (TREND, FB LEADS, BANDI/FIERE, POST AI) ─────────────

class RadarTrendsRequest(BaseModel):
    search_id: str = "ds-master-clean"
    niche: str = "termoidraulica"
    geography: str = "sicilia"
    timeframe: str = "30d"


class RadarFacebookRequest(BaseModel):
    search_id: str = "ds-master-clean"
    niche: str = "all"
    limit: int = Field(default=12, ge=1, le=30)


class RadarSectorNewsRequest(BaseModel):
    niche: str = "termoidraulica"
    geography: str = "sicilia"
    category: str = "all"


class RadarSocialPostsRequest(BaseModel):
    topic: str = Field(..., min_length=3)
    niche: str = "termoidraulica"
    geography: str = "sicilia"
    tone: str = "Tecnico-Pratico (da cantiere)"
    target_platform: Optional[str] = None
    instruction: str = ""


@app.post("/radar/trends")
async def api_radar_trends(req: RadarTrendsRequest, _user: Dict[str, Any] = Depends(require_auth)):
    leads = load_search_leads(req.search_id)
    radar = MarketRadarService()
    return await radar.discover_trends(
        leads=leads,
        niche=req.niche,
        geography=req.geography,
        timeframe=req.timeframe,
    )


@app.post("/radar/facebook-leads")
async def api_radar_facebook_leads(req: RadarFacebookRequest, _user: Dict[str, Any] = Depends(require_auth)):
    leads = load_search_leads(req.search_id)
    radar = MarketRadarService()
    return await radar.analyze_lead_facebook_pages(
        leads=leads,
        niche=req.niche,
        limit=req.limit,
    )


@app.post("/radar/sector-news")
async def api_radar_sector_news(req: RadarSectorNewsRequest, _user: Dict[str, Any] = Depends(require_auth)):
    radar = MarketRadarService()
    return await radar.fetch_sector_news(
        niche=req.niche,
        geography=req.geography,
        category=req.category,
    )


@app.post("/radar/social-posts")
async def api_radar_social_posts(req: RadarSocialPostsRequest, _user: Dict[str, Any] = Depends(require_auth)):
    radar = MarketRadarService()
    return await radar.generate_social_posts(
        topic=req.topic,
        niche=req.niche,
        geography=req.geography,
        tone=req.tone,
        target_platform=req.target_platform,
        instruction=req.instruction,
    )
