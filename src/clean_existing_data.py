"""
clean_existing_data.py — Bonifica idempotente, deduplica gerarchica,
normalizzazione E.164, filtro anti-GDO e crawl live dei siti aziendali reali.
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import pandas as pd
from crawl4ai import AsyncWebCrawler

from src.config import (
    CSV_DIR,
    DATA_DIR,
    OUTPUT_DASHBOARD_CSV,
    OUTPUT_DISCOVERED_CSV,
    OUTPUT_DISCOVERED_EXCEL,
    WEBSITE_CRAWL_CACHE_FILE,
)
from src.normalizers import (
    clean_company_website,
    is_anti_persona_retail,
    is_maltese_or_foreign_record,
    is_valid_company_website,
    normalize_city_and_area,
    normalize_email,
    normalize_phone_e164,
)
from src.piva_validator import clean_piva, validate_piva
from src.pipeline import _style_excel_workbook, export_all_outputs
from src.website_crawler import fetch_website_intelligence

logger = logging.getLogger("clean_existing_data")


def _load_crawl_cache() -> Dict[str, Dict[str, Any]]:
    if WEBSITE_CRAWL_CACHE_FILE.exists():
        try:
            return json.loads(WEBSITE_CRAWL_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Cache crawl corrotta, riparto da zero: {e}")
    return {}


def _save_crawl_cache(cache: Dict[str, Dict[str, Any]]):
    WEBSITE_CRAWL_CACHE_FILE.parent.mkdir(exist_ok=True)
    WEBSITE_CRAWL_CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _norm_company_key(name: str) -> str:
    s = (name or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _canonical_piva(raw: str) -> str:
    cleaned = clean_piva(str(raw or ""))
    if cleaned and validate_piva(cleaned):
        return f"IT{cleaned}"
    return ""


def _status_rank(stato: str) -> int:
    s = str(stato or "").upper()
    if "ASSOCIATO RILEVATO" in s:
        return 3
    if "NON ASSOCIATO" in s:
        return 2
    if "DA VERIFICARE" in s:
        return 1
    return 0


def _merge_records(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """Unisce due record della stessa impresa preservando sempre i campi più ricchi e reali."""
    merged = dict(existing)

    # Campi scalari: riempi se mancanti o migliora
    for field in (
        "Email", "Website", "Partita_IVA", "P_IVA_Numerica", "Fonte_PIVA",
        "Category", "Address", "Nicchia_Target", "Area_Geografica",
        "Evidenza_CNA", "Data_Scoperta", "Google Rating", "Total Reviews",
        "Google Maps URL", "Facebook URL", "Google Places ID", "Prospect ID", "Tags",
    ):
        cur_val = str(merged.get(field, "") or "").strip()
        new_val = str(incoming.get(field, "") or "").strip()
        if not cur_val and new_val:
            merged[field] = new_val
        elif field == "Website" and new_val and not is_valid_company_website(cur_val) and is_valid_company_website(new_val):
            merged[field] = new_val

    # Telefoni: preserva e combina primario + secondario privilegiando mobile E.164
    all_raw_phones = " / ".join(
        x for x in (
            merged.get("Phone", ""),
            merged.get("Phone_Secondary", ""),
            incoming.get("Phone", ""),
            incoming.get("Phone_Secondary", ""),
        ) if str(x or "").strip()
    )
    p1, p2 = normalize_phone_e164(all_raw_phones)
    merged["Phone"] = p1
    merged["Phone_Secondary"] = p2

    # Stato CNA: mantieni lo stato più informativo (Associato > Non Associato > Da Verificare)
    if _status_rank(incoming.get("Stato_CNA", "")) > _status_rank(merged.get("Stato_CNA", "")):
        merged["Stato_CNA"] = incoming.get("Stato_CNA", "")
        if incoming.get("Evidenza_CNA"):
            merged["Evidenza_CNA"] = incoming["Evidenza_CNA"]

    return merged


def _load_and_merge_all_sources() -> List[Dict[str, Any]]:
    """
    Carica tutti i file sorgenti e intermedi in ordine di affidabilità informativa,
    rimuovendo record esteri/GDO e unificando i duplicati per P.IVA, telefono e (nome, città).
    """
    csv_files_map = {
        "Clean_1_HVAC_Climatizzazione_Riscaldamento.csv": "HVAC & Climatizzazione",
        "Clean_2_Termoidraulica_Idraulici.csv": "Termoidraulica & Idraulica",
        "Clean_3_Impianti_Elettrici_Elettricisti.csv": "Impianti Elettrici",
        "Clean_4_Impianti_Generali_Assistenza_Altri.csv": "Impiantistica Generale",
    }

    raw_rows: List[Dict[str, Any]] = []

    # 1. File sorgenti CSV_Leads (hanno siti reali verificati e telefoni puliti)
    for fn, niche in csv_files_map.items():
        p = CSV_DIR / fn
        if p.exists():
            df = pd.read_csv(p, dtype=str).fillna("")
            df["Nicchia_Target"] = niche
            df["Origine_File"] = fn
            raw_rows.extend(df.to_dict(orient="records"))

    # 2. File generati in data/ (associati, arricchiti con siti reali, scoperte, termoidraulica, tutte)
    data_sources = [
        "associati_rilevati.csv",
        "leads_arricchiti.csv",
        "nuove_lead_scoperte.csv",
        "termoidraulica_catania_provincia.csv",
        "tutte_le_lead.csv",
    ]
    for fn in data_sources:
        p = DATA_DIR / fn
        if p.exists():
            df = pd.read_csv(p, dtype=str).fillna("")
            raw_rows.extend(df.to_dict(orient="records"))

    records: List[Dict[str, Any]] = []
    piva_idx: Dict[str, int] = {}
    phone_idx: Dict[str, int] = {}
    name_city_idx: Dict[Tuple[str, str], int] = {}

    for raw in raw_rows:
        if is_maltese_or_foreign_record(raw):
            continue

        comp_name = str(raw.get("Company Name", "")).strip()
        if not comp_name:
            continue
        category = str(raw.get("Category", "")).strip()
        clean_web = clean_company_website(raw.get("Website", ""))

        if is_anti_persona_retail(comp_name, category, clean_web):
            continue

        piva_it = _canonical_piva(raw.get("Partita_IVA", "") or raw.get("P_IVA_Numerica", ""))
        piva_num = piva_it[2:] if piva_it else ""
        p1, p2 = normalize_phone_e164(raw.get("Phone", ""))
        email = normalize_email(raw.get("Email", ""))
        city, area = normalize_city_and_area(raw.get("City", ""), raw.get("Address", ""))

        cleaned_row: Dict[str, Any] = {
            **raw,
            "Company Name": comp_name,
            "City": city,
            "Area_Geografica": area,
            "Phone": p1,
            "Phone_Secondary": p2,
            "Email": email,
            "Website": clean_web,
            "Partita_IVA": piva_it,
            "P_IVA_Numerica": piva_num,
        }

        # Ricerca match esistente in ordine gerarchico: P.IVA -> Telefono -> (Nome, Città)
        target_idx: Optional[int] = None
        if piva_it and piva_it in piva_idx:
            target_idx = piva_idx[piva_it]
        elif p1 and p1 in phone_idx:
            target_idx = phone_idx[p1]
        else:
            nc_key = (_norm_company_key(comp_name), city.lower())
            if nc_key in name_city_idx:
                target_idx = name_city_idx[nc_key]

        if target_idx is not None:
            merged = _merge_records(records[target_idx], cleaned_row)
            records[target_idx] = merged
        else:
            target_idx = len(records)
            records.append(cleaned_row)

        rec = records[target_idx]
        if rec.get("Partita_IVA"):
            piva_idx[rec["Partita_IVA"]] = target_idx
        if rec.get("Phone"):
            phone_idx[rec["Phone"]] = target_idx
        name_city_idx[(_norm_company_key(rec["Company Name"]), rec["City"].lower())] = target_idx

    logger.info(f"Unificati {len(raw_rows)} record grezzi in {len(records)} aziende uniche pulite.")
    return records


async def _live_crawl_real_websites(
    records: List[Dict[str, Any]],
    use_crawl4ai_fallback: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """Scansiona tutti i siti aziendali reali non ancora presenti in cache."""
    cache = _load_crawl_cache()
    unique_urls = sorted({r["Website"] for r in records if is_valid_company_website(r.get("Website", ""))})
    to_fetch = [u for u in unique_urls if u not in cache]

    logger.info(
        f"Siti web aziendali reali unici: {len(unique_urls)} | In cache: {len(unique_urls) - len(to_fetch)} | Da scansionare live: {len(to_fetch)}"
    )

    if not to_fetch:
        return cache

    sem = asyncio.Semaphore(12)
    connector = aiohttp.TCPConnector(limit=24)

    async def _worker(session: aiohttp.ClientSession, url: str):
        async with sem:
            try:
                res = await fetch_website_intelligence(session, url, crawler=None, max_subpages=2)
                cache[url] = res
            except Exception as e:
                logger.debug(f"Errore crawl live {url}: {e}")
                cache[url] = {
                    "piva": None,
                    "cna_affiliato": False,
                    "cna_dettaglio": "Sito non raggiungibile",
                    "crawl_status": "ERROR",
                    "piva_source": "NOT_FOUND",
                    "pages_scanned": 0,
                    "text_snippet": "",
                    "email": "",
                    "phone": "",
                }

    async with aiohttp.ClientSession(connector=connector) as session:
        await asyncio.gather(*(_worker(session, u) for u in to_fetch))

    # Eventuale passata Crawl4AI solo per siti che hanno risposto HTTP 200 ma testo quasi vuoto (SPA JS)
    if use_crawl4ai_fallback:
        js_candidates = [
            u for u in to_fetch
            if cache.get(u, {}).get("crawl_status") == "SUCCESS"
            and len(cache.get(u, {}).get("text_snippet", "")) < 150
        ]
        if js_candidates:
            logger.info(f"Fallback Crawl4AI su {len(js_candidates)} siti JS-rendered...")
            try:
                async with aiohttp.ClientSession() as session:
                    async with AsyncWebCrawler() as crawler:
                        for u in js_candidates[:25]:
                            try:
                                res = await fetch_website_intelligence(session, u, crawler=crawler, max_subpages=1)
                                if len(res.get("text_snippet", "")) > len(cache[u].get("text_snippet", "")):
                                    cache[u] = res
                            except Exception:
                                continue
            except Exception as e:
                logger.warning(f"Fallback Crawl4AI saltato per errore browser: {e}")

    _save_crawl_cache(cache)
    return cache


def _apply_website_intelligence(records: List[Dict[str, Any]], cache: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Applica i dati reali estratti dai siti web e aggiorna stato CNA / P.IVA / Email / Telefono."""
    for r in records:
        web = r.get("Website", "")
        intel = cache.get(web) if web else None

        if intel:
            r["Website_Text_Snippet"] = intel.get("text_snippet", "")
            if not r.get("Email") and intel.get("email"):
                r["Email"] = normalize_email(intel["email"])
            if not r.get("Phone") and intel.get("phone"):
                p1, p2 = normalize_phone_e164(intel["phone"])
                if p1:
                    r["Phone"] = p1
                    if p2 and not r.get("Phone_Secondary"):
                        r["Phone_Secondary"] = p2
            if not r.get("Partita_IVA") and intel.get("piva") and validate_piva(intel["piva"]):
                r["Partita_IVA"] = f"IT{intel['piva']}"
                r["P_IVA_Numerica"] = intel["piva"]
                r["Fonte_PIVA"] = "WEBSITE_CRAWL"

            if intel.get("cna_affiliato"):
                r["Stato_CNA"] = "🟢 ASSOCIATO RILEVATO (Convenzione TecnicoLIVE)"
                r["Evidenza_CNA"] = intel.get("cna_dettaglio", "")

        # Normalizza stato commerciale coerente
        stato_cur = str(r.get("Stato_CNA", ""))
        has_piva = bool(r.get("Partita_IVA"))

        if "ASSOCIATO RILEVATO" in stato_cur:
            r["Stato_CNA"] = "🟢 ASSOCIATO RILEVATO (Convenzione TecnicoLIVE)"
            r["Azione_Commerciale_Consigliata"] = "Proporre assistente vocale AI TecnicoLIVE per soci CNA Catania"
        elif has_piva:
            r["Stato_CNA"] = "🔵 NON ASSOCIATO (Target Tesseramento CNA)"
            r["Azione_Commerciale_Consigliata"] = "Proporre TecnicoLIVE + Iscrizione CNA Catania al 50% per il 1° anno"
        else:
            r["Stato_CNA"] = "🟡 DA VERIFICARE (P.IVA mancante)"
            r["Azione_Commerciale_Consigliata"] = "Verificare manualmente P.IVA e recapiti per controllo con Ufficio Soci CNA"

    return records


async def run_data_cleanup(live_crawl: bool = False, use_crawl4ai_fallback: bool = True) -> Dict[str, int]:
    """
    Esegue la bonifica completa dei dataset in data/ e exports_excel/:
    1. Carica e unifica CSV_Leads/ e data/*.csv
    2. Elimina portali, record esteri/Malta e catene GDO/Anti-Personas
    3. Deduplica gerarchicamente per P.IVA, Telefono e (Nome, Città)
    4. Esegue crawl live sui siti reali (se live_crawl=True) o usa cache esistente
    5. Arricchisce con Clay Engine (Zero Hallucination) ed esporta tutto in modo sincronizzato
    """
    logger.info("=== Avvio Bonifica & Sincronizzazione Dataset TecnicoLIVE ===")
    records = _load_and_merge_all_sources()

    if live_crawl:
        cache = await _live_crawl_real_websites(records, use_crawl4ai_fallback=use_crawl4ai_fallback)
    else:
        cache = _load_crawl_cache()

    records = _apply_website_intelligence(records, cache)
    master_df = pd.DataFrame(records)

    # Deduplica finale difensiva su P.IVA (nel caso il crawl abbia scoperto P.IVA identiche)
    if not master_df.empty:
        has_piva = master_df["Partita_IVA"].astype(str).str.startswith("IT")
        df_with_piva = master_df[has_piva].drop_duplicates(subset=["Partita_IVA"], keep="first")
        df_no_piva = master_df[~has_piva]
        master_df = pd.concat([df_with_piva, df_no_piva], ignore_index=True)

    summary = export_all_outputs(master_df)

    # Sincronizza anche nuove_lead_scoperte.csv, target_cna_nuovi.csv e nuove_lead_scoperte.xlsx dal master pulito
    if OUTPUT_DASHBOARD_CSV.exists():
        dash_clean = pd.read_csv(OUTPUT_DASHBOARD_CSV, dtype=str).fillna("")
        disc_clean = dash_clean[dash_clean["Data_Scoperta"].str.strip() != ""].copy()
        if disc_clean.empty:
            disc_clean = dash_clean.copy()
        disc_clean.to_csv(OUTPUT_DISCOVERED_CSV, index=False, encoding="utf-8-sig")
        target_new = disc_clean[disc_clean["Stato_CNA"].str.contains("NON ASSOCIATO", na=False)].copy()
        target_new.to_csv(DATA_DIR / "target_cna_nuovi.csv", index=False, encoding="utf-8-sig")
        with pd.ExcelWriter(OUTPUT_DISCOVERED_EXCEL, engine="openpyxl") as writer:
            disc_clean.to_excel(writer, sheet_name="Nuove Lead Scoperte", index=False)
            target_new.to_excel(writer, sheet_name="Target CNA Nuovi", index=False)
        _style_excel_workbook(OUTPUT_DISCOVERED_EXCEL, header_color="1F4E78")

    logger.info(f"=== Bonifica Completata: {summary} ===")
    return summary


if __name__ == "__main__":
    asyncio.run(run_data_cleanup(live_crawl=True))
