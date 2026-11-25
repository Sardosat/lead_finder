"""
Scanner Massivo Territoriale Termoidraulica Catania & Provincia
Estrae tutte le ditte di termoidraulica, caldaie, riscaldamento e idraulica
nei comuni della Città Metropolitana di Catania, con filtri anti-GDO,
normalizzazione E.164, verifica web reale CNA e arricchimento Clay Engine.
"""

import asyncio
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import aiohttp
import pandas as pd

from src.config import DATA_DIR, OUTPUT_DASHBOARD_CSV
from src.normalizers import (
    clean_company_website,
    is_anti_persona_retail,
    normalize_city_and_area,
    normalize_email,
)
from src.paginegialle_client import fetch_profile_details, scrape_all_pages
from src.pipeline import export_all_outputs, is_maltese_or_foreign
from src.piva_validator import clean_piva
from src.territory_data import CATANIA_MUNICIPALITIES
from src.website_crawler import fetch_website_intelligence

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("termoidraulica_scanner")

TERMO_QUERIES = [
    {"query": "termoidraulica", "niche": "Termoidraulica & Idraulica"},
    {"query": "caldaie", "niche": "HVAC & Climatizzazione"},
    {"query": "idraulici", "niche": "Termoidraulica & Idraulica"},
    {"query": "assistenza-caldaie", "niche": "HVAC & Climatizzazione"},
    {"query": "riscaldamento-impianti", "niche": "HVAC & Climatizzazione"},
    {"query": "climatizzatori", "niche": "HVAC & Climatizzazione"},
    {"query": "impianti-idraulici", "niche": "Termoidraulica & Idraulica"},
]


def load_known_leads() -> Tuple[Set[str], Set[str], Set[str], pd.DataFrame]:
    """Carica le lead storiche dal master completo per evitare duplicati."""
    known_names: Set[str] = set()
    known_pivas: Set[str] = set()
    known_phones: Set[str] = set()
    df_existing = pd.DataFrame()

    master_path = OUTPUT_DASHBOARD_CSV if OUTPUT_DASHBOARD_CSV.exists() else (DATA_DIR / "campagna_outbound_tecnicolive.csv")
    if master_path.exists():
        try:
            df_existing = pd.read_csv(master_path, dtype=str).fillna("")
            for _, r in df_existing.iterrows():
                name = r.get("Company Name", "").strip().lower()
                if name:
                    known_names.add(name)
                p = clean_piva(r.get("Partita_IVA", ""))
                if p:
                    known_pivas.add(p)
                ph = re.sub(r"[^\d]", "", r.get("Phone", ""))
                if ph and len(ph) >= 7:
                    known_phones.add(ph[-8:])
        except Exception as e:
            logger.warning(f"Errore lettura master lead: {e}")

    return known_names, known_pivas, known_phones, df_existing


async def run_termoidraulica_scan(max_municipalities: Optional[int] = None) -> pd.DataFrame:
    """Esegue la scansione provinciale Termoidraulica e aggiorna l'intero ecosistema CSV/Excel."""
    known_names, known_pivas, _, df_existing = load_known_leads()
    logger.info(f"Avvio Scansione Termoidraulica Catania & Provincia | Lead storiche: {len(known_names)}")

    municipalities = CATANIA_MUNICIPALITIES[:max_municipalities] if max_municipalities else CATANIA_MUNICIPALITIES
    new_discovered: List[Dict[str, Any]] = []
    seen_in_session: Set[str] = set()
    sem = asyncio.Semaphore(5)

    async with aiohttp.ClientSession() as session:
        for idx, muni in enumerate(municipalities, 1):
            c_name = muni["name"]
            c_slug = muni["slug"]
            area = muni["area"]

            logger.info(f"[{idx}/{len(municipalities)}] Scansione Termoidraulica: {c_name.upper()} ({area})")

            for q_item in TERMO_QUERIES:
                q = q_item["query"]
                niche = q_item["niche"]

                cards = await scrape_all_pages(session, q, c_slug, max_pages=5, semaphore=sem)
                if not cards:
                    continue

                for item in cards:
                    raw_name = item["name"]
                    c_name_key = raw_name.lower().strip()

                    if is_anti_persona_retail(raw_name, item.get("category", "")):
                        continue
                    if c_name_key in known_names or c_name_key in seen_in_session:
                        continue
                    seen_in_session.add(c_name_key)

                    details = await fetch_profile_details(session, item["profile_url"], semaphore=sem)
                    piva = details.get("piva")
                    website = clean_company_website(details.get("website") or "")
                    email = normalize_email(details.get("email") or "")

                    if is_anti_persona_retail(raw_name, item.get("category", ""), website):
                        continue
                    if piva and piva in known_pivas:
                        continue

                    text_snippet = ""
                    cna_found = False
                    cna_detail = ""
                    crawl_ok = False
                    phone_primary = item["phone"]

                    if website:
                        web_intel = await fetch_website_intelligence(session, website, crawler=None)
                        text_snippet = web_intel.get("text_snippet", "")
                        crawl_ok = web_intel.get("crawl_status") == "SUCCESS"
                        cna_found = bool(web_intel.get("cna_affiliato"))
                        cna_detail = web_intel.get("cna_dettaglio", "")
                        if not email and web_intel.get("email"):
                            email = web_intel["email"]
                        if not phone_primary and web_intel.get("phone"):
                            phone_primary = web_intel["phone"]
                        if not piva and web_intel.get("piva"):
                            piva = web_intel["piva"]

                    if cna_found:
                        stato_cna = "🟢 ASSOCIATO RILEVATO (Convenzione TecnicoLIVE)"
                        azione = "Proporre assistente vocale AI TecnicoLIVE per soci CNA Catania"
                    elif piva and crawl_ok:
                        stato_cna = "🔵 NON ASSOCIATO (Target Tesseramento CNA)"
                        azione = "Proporre TecnicoLIVE + Iscrizione CNA Catania al 50% per il 1° anno"
                    elif piva:
                        stato_cna = "🟡 DA VERIFICARE (P.IVA validata, verifica CNA pendente)"
                        azione = "Verificare con Ufficio Soci CNA Catania"
                    else:
                        stato_cna = "🟡 DA VERIFICARE (P.IVA mancante)"
                        azione = "Verificare manualmente P.IVA e affiliazione CNA"

                    city_clean, area_clean = normalize_city_and_area(c_name, item.get("address", ""))
                    new_discovered.append(
                        {
                            "Company Name": raw_name,
                            "Nicchia_Target": niche,
                            "Category": item["category"],
                            "City": city_clean,
                            "Area_Geografica": area_clean,
                            "Address": item["address"] or f"{city_clean} (CT)",
                            "Phone": phone_primary,
                            "Phone_Secondary": item.get("phone_secondary", ""),
                            "Email": email,
                            "Website": website,
                            "Partita_IVA": f"IT{piva}" if piva else "",
                            "P_IVA_Numerica": piva or "",
                            "Fonte_PIVA": "DIRECTORY_PROFILE" if piva else "NOT_FOUND",
                            "Stato_CNA": stato_cna,
                            "Evidenza_CNA": cna_detail,
                            "Azione_Commerciale_Consigliata": azione,
                            "Website_Text_Snippet": text_snippet,
                            "Data_Scoperta": pd.Timestamp.now().strftime("%Y-%m-%d"),
                        }
                    )

                await asyncio.sleep(0.1)

    logger.info(f"Scansione completata: trovate {len(new_discovered)} NUOVE ditte uniche di termoidraulica.")

    df_new = pd.DataFrame(new_discovered)
    if not df_new.empty:
        df_new = df_new[~df_new.apply(is_maltese_or_foreign, axis=1)].copy()
        combined_master = pd.concat([df_existing, df_new], ignore_index=True) if not df_existing.empty else df_new
        combined_master.drop_duplicates(subset=["Company Name", "City"], keep="first", inplace=True)
        export_all_outputs(combined_master)
    elif not df_existing.empty:
        export_all_outputs(df_existing)

    return pd.read_csv(DATA_DIR / "termoidraulica_catania_provincia.csv", dtype=str).fillna("")


if __name__ == "__main__":
    asyncio.run(run_termoidraulica_scan())
