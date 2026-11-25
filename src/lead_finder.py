import asyncio
import logging
import urllib.parse
from typing import Any, Dict, List, Optional, Set, Tuple

import aiohttp
import pandas as pd
from crawl4ai import AsyncWebCrawler

from src.config import (
    DATA_DIR,
    OUTPUT_CSV_ENRICHED,
    OUTPUT_DISCOVERED_CSV,
    OUTPUT_DISCOVERED_EXCEL,
)
from src.normalizers import (
    clean_company_website,
    is_anti_persona_retail,
    normalize_city_and_area,
    normalize_email,
)
from src.paginegialle_client import (
    fetch_profile_details as pg_fetch_profile_details,
    scrape_listing_page,
)
from src.pipeline import (
    export_all_outputs,
    generate_outbound_pitch,
    is_maltese_or_foreign,
)
from src.piva_validator import clean_piva
from src.website_crawler import fetch_website_intelligence, normalize_url

logger = logging.getLogger("lead_finder")

PROVINCE_CITIES = [
    "catania",
    "acireale",
    "misterbianco",
    "paterno",
    "giarre",
    "mascalucia",
    "gravina-di-catania",
    "caltagirone",
    "belpasso",
    "san-giovanni-la-punta",
    "aci-castello",
]

BASE_QUERIES = [
    {"query": "climatizzatori", "niche": "HVAC & Climatizzazione"},
    {"query": "caldaie", "niche": "HVAC & Climatizzazione"},
    {"query": "termoidraulica", "niche": "Termoidraulica & Idraulica"},
    {"query": "idraulici", "niche": "Termoidraulica & Idraulica"},
    {"query": "elettricisti", "niche": "Impianti Elettrici"},
    {"query": "impianti-elettrici", "niche": "Impianti Elettrici"},
    {"query": "impianti-industriali", "niche": "Impiantistica Generale"},
]


def load_known_identifiers() -> Tuple[Set[str], Set[str], Set[str]]:
    """Carica P.IVA, domini web aziendali reali e nomi già presenti per deduplica."""
    known_pivas: Set[str] = set()
    known_domains: Set[str] = set()
    known_names: Set[str] = set()

    if OUTPUT_CSV_ENRICHED.exists():
        try:
            df = pd.read_csv(OUTPUT_CSV_ENRICHED, dtype=str).fillna("")
            for _, r in df.iterrows():
                p = clean_piva(r.get("Partita_IVA", ""))
                if p:
                    known_pivas.add(p)
                w = normalize_url(r.get("Website", ""))
                if w:
                    dom = urllib.parse.urlparse(w).netloc.lower().replace("www.", "")
                    if dom:
                        known_domains.add(dom)
                name = r.get("Company Name", "").strip().lower()
                if name:
                    known_names.add(name)
        except Exception as e:
            logger.warning(f"Impossibile leggere file arricchito per deduplica: {e}")

    return known_pivas, known_domains, known_names


async def fetch_profile_details(session: aiohttp.ClientSession, profile_url: str) -> Dict[str, Any]:
    """Wrapper retrocompatibile verso il client unificato PagineGialle."""
    return await pg_fetch_profile_details(session, profile_url)


async def scrape_directory_listing(
    session: aiohttp.ClientSession,
    query: str,
    city: str,
    page: int = 1,
) -> List[Dict[str, Any]]:
    """Wrapper retrocompatibile verso il client unificato PagineGialle."""
    return await scrape_listing_page(session, query, city, page=page)


async def discover_new_leads(
    max_leads_per_sector: int = 15,
    verify_with_crawl4ai: bool = True,
    target_city: Optional[str] = None,
    all_cities: bool = False,
) -> pd.DataFrame:
    """
    Cerca nuove lead nei settori chiave, estrae P.IVA, sito web reale (no portali),
    deduplica rispetto al database e verifica affiliazione CNA Catania.
    """
    known_pivas, known_domains, known_names = load_known_identifiers()
    logger.info(
        f"Filtro deduplica attivo: {len(known_pivas)} P.IVA, {len(known_domains)} domini, {len(known_names)} nomi noti"
    )

    discovered: List[Dict[str, Any]] = []
    seen_in_session: Set[str] = set()
    sem = asyncio.Semaphore(5)

    if target_city:
        cities_to_scan = [target_city.lower().strip()]
    elif all_cities:
        cities_to_scan = PROVINCE_CITIES
    else:
        cities_to_scan = ["catania"]

    async with aiohttp.ClientSession() as session:
        for city in cities_to_scan:
            for bq in BASE_QUERIES:
                query = bq["query"]
                niche = bq["niche"]

                logger.info(f"--- Ricerca: '{query}' a {city.capitalize()} (Nicchia: {niche}) ---")
                raw_items = await scrape_listing_page(session, query, city, page=1, semaphore=sem)
                if len(raw_items) < 8:
                    raw_items += await scrape_listing_page(session, query, city, page=2, semaphore=sem)

                collected_for_sector = 0
                for item in raw_items:
                    if collected_for_sector >= max_leads_per_sector:
                        break

                    name = item["name"]
                    clean_name = name.lower().strip()

                    if is_anti_persona_retail(name, item.get("category", "")):
                        continue
                    if clean_name in known_names or clean_name in seen_in_session:
                        continue
                    seen_in_session.add(clean_name)

                    profile_url = item.get("profile_url")
                    details = {"piva": None, "website": None, "email": None}
                    if profile_url:
                        details = await pg_fetch_profile_details(session, profile_url, semaphore=sem)

                    piva = details.get("piva")
                    website = clean_company_website(details.get("website") or "")
                    email = normalize_email(details.get("email") or "")

                    if is_anti_persona_retail(name, item.get("category", ""), website):
                        continue
                    if piva and piva in known_pivas:
                        continue
                    if website:
                        dom = urllib.parse.urlparse(website).netloc.lower().replace("www.", "")
                        if dom in known_domains:
                            continue

                    comune, area = normalize_city_and_area(city.replace("-", " "), item.get("address", ""))

                    lead_entry = {
                        "Company Name": name,
                        "Nicchia_Target": niche,
                        "Category": item["category"],
                        "City": comune,
                        "Area_Geografica": area,
                        "Address": item["address"] or f"{comune} (CT)",
                        "Phone": item["phone"],
                        "Phone_Secondary": item.get("phone_secondary", ""),
                        "Email": email,
                        "Website": website,
                        "Partita_IVA": f"IT{piva}" if piva else "",
                        "P_IVA_Numerica": piva or "",
                        "Fonte_PIVA": "DIRECTORY_PROFILE" if piva else "NOT_FOUND",
                        "Stato_CNA": "🟡 DA VERIFICARE (verifica CNA pendente)",
                        "Evidenza_CNA": "",
                        "Azione_Commerciale_Consigliata": "Verificare affiliazione CNA",
                        "Pitch_Commerciale_TecnicoLIVE": "",
                        "Website_Text_Snippet": "",
                        "Data_Scoperta": pd.Timestamp.now().strftime("%Y-%m-%d"),
                    }

                    discovered.append(lead_entry)
                    collected_for_sector += 1
                    logger.info(
                        f"  + Trovata NUOVA Lead: {name} ({comune}) | Tel: {item['phone'] or 'N/D'} | P.IVA: {lead_entry['Partita_IVA'] or 'No'}"
                    )
                    await asyncio.sleep(0.25)

    logger.info(f"Totale nuove lead uniche trovate: {len(discovered)}")

    if verify_with_crawl4ai and discovered:
        logger.info("Avvio verifica siti web aziendali reali e affiliazione CNA...")
        async with aiohttp.ClientSession() as session:
            async with AsyncWebCrawler() as crawler:
                for lead in discovered:
                    web = lead.get("Website")
                    if web:
                        crawl_res = await fetch_website_intelligence(session, web, crawler=crawler)
                        lead["Website_Text_Snippet"] = crawl_res.get("text_snippet", "")
                        if not lead["Email"] and crawl_res.get("email"):
                            lead["Email"] = crawl_res["email"]
                        if not lead["Phone"] and crawl_res.get("phone"):
                            lead["Phone"] = crawl_res["phone"]
                        if not lead["Partita_IVA"] and crawl_res.get("piva"):
                            lead["Partita_IVA"] = f"IT{crawl_res['piva']}"
                            lead["P_IVA_Numerica"] = crawl_res["piva"]
                            lead["Fonte_PIVA"] = "WEBSITE_CRAWL"

                        if crawl_res.get("cna_affiliato"):
                            lead["Stato_CNA"] = "🟢 ASSOCIATO RILEVATO (Convenzione TecnicoLIVE)"
                            lead["Evidenza_CNA"] = crawl_res.get("cna_dettaglio", "")
                            lead["Azione_Commerciale_Consigliata"] = "Proporre assistente vocale AI TecnicoLIVE per soci CNA Catania"
                        elif lead["Partita_IVA"] and crawl_res.get("crawl_status") == "SUCCESS":
                            lead["Stato_CNA"] = "🔵 NON ASSOCIATO (Target Tesseramento CNA)"
                            lead["Azione_Commerciale_Consigliata"] = "Proporre TecnicoLIVE + Iscrizione CNA Catania al 50% per il 1° anno"
                        elif lead["Partita_IVA"]:
                            lead["Stato_CNA"] = "🟡 DA VERIFICARE (P.IVA validata, verifica CNA pendente)"
                            lead["Azione_Commerciale_Consigliata"] = "Verificare con Ufficio Soci CNA Catania"
                    elif lead["Partita_IVA"]:
                        lead["Stato_CNA"] = "🟡 DA VERIFICARE (P.IVA validata, verifica CNA pendente)"
                        lead["Azione_Commerciale_Consigliata"] = "Verificare con Ufficio Soci CNA Catania"

                    lead["Pitch_Commerciale_TecnicoLIVE"] = generate_outbound_pitch(
                        lead["Company Name"], lead["Nicchia_Target"], lead["Stato_CNA"], lead["City"]
                    )

    return pd.DataFrame(discovered)


def save_discovered_leads(df_new: pd.DataFrame):
    """Salva le nuove lead pulite in formato CSV/Excel e aggiorna l'intero ecosistema output."""
    if df_new.empty:
        logger.info("Nessuna nuova lead da salvare.")
        return

    df_new = df_new[~df_new.apply(is_maltese_or_foreign, axis=1)].copy()
    df_new = df_new[
        ~df_new.apply(
            lambda r: is_anti_persona_retail(
                r.get("Company Name", ""), r.get("Category", ""), r.get("Website", "")
            ),
            axis=1,
        )
    ].copy()

    df_new.to_csv(OUTPUT_DISCOVERED_CSV, index=False, encoding="utf-8-sig")
    target_new = df_new[df_new["Stato_CNA"].str.contains("NON ASSOCIATO", na=False)]
    target_new.to_csv(DATA_DIR / "target_cna_nuovi.csv", index=False, encoding="utf-8-sig")

    with pd.ExcelWriter(OUTPUT_DISCOVERED_EXCEL, engine="openpyxl") as writer:
        df_new.to_excel(writer, sheet_name="Nuove Lead Scoperte", index=False)
        target_new.to_excel(writer, sheet_name="Target CNA Nuovi", index=False)

    logger.info(f"Nuove lead salvate in CSV ({OUTPUT_DISCOVERED_CSV}) ed Excel ({OUTPUT_DISCOVERED_EXCEL})")

    if OUTPUT_CSV_ENRICHED.exists():
        existing_df = pd.read_csv(OUTPUT_CSV_ENRICHED, dtype=str).fillna("")
        combined_df = pd.concat([existing_df, df_new], ignore_index=True)
        combined_df.drop_duplicates(subset=["Company Name", "City"], keep="first", inplace=True)
        export_all_outputs(combined_df)
    else:
        export_all_outputs(df_new)
