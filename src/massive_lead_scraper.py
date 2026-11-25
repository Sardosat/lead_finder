import asyncio
import logging
import urllib.parse
from typing import Any, Dict, List, Optional, Set

import aiohttp
import pandas as pd
from crawl4ai import AsyncWebCrawler

from src.config import DATA_DIR
from src.lead_finder import load_known_identifiers
from src.normalizers import (
    clean_company_website,
    is_anti_persona_retail,
    normalize_email,
)
from src.paginegialle_client import fetch_profile_details, scrape_all_pages
from src.pipeline import generate_outbound_pitch
from src.territory_data import CATANIA_MUNICIPALITIES, SEARCH_QUERIES
from src.website_crawler import fetch_website_intelligence

logger = logging.getLogger("massive_scraper")


async def run_territory_scan(
    selected_municipalities: Optional[List[Dict[str, str]]] = None,
    verify_cna: bool = True,
    save_callback=None,
) -> pd.DataFrame:
    """
    Esegue la scansione esaustiva dei comuni della provincia di Catania
    sulle 12 query verticali tramite il client unificato PagineGialle con semaforo reale.
    """
    municipalities = selected_municipalities or CATANIA_MUNICIPALITIES
    known_pivas, known_domains, known_names = load_known_identifiers()
    logger.info(
        f"Avvio Scansione Territoriale su {len(municipalities)} comuni | Lead già a sistema: {len(known_names)}"
    )

    discovered: List[Dict[str, Any]] = []
    seen_in_session: Set[str] = set()
    sem = asyncio.Semaphore(5)

    async with aiohttp.ClientSession() as session:
        for m_idx, muni in enumerate(municipalities, 1):
            city_name = muni["name"]
            city_slug = muni["slug"]
            area = muni["area"]

            logger.info(f"\n[{m_idx}/{len(municipalities)}] === Scansione Comune: {city_name.upper()} (Area: {area}) ===")

            for q_item in SEARCH_QUERIES:
                query = q_item["query"]
                niche = q_item["niche"]

                raw_leads = await scrape_all_pages(session, query, city_slug, max_pages=10, semaphore=sem)
                if not raw_leads:
                    continue

                new_in_query = 0
                for item in raw_leads:
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
                        details = await fetch_profile_details(session, profile_url, semaphore=sem)

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

                    lead_entry = {
                        "Company Name": name,
                        "Nicchia_Target": niche,
                        "Category": item["category"],
                        "City": city_name,
                        "Area_Geografica": area,
                        "Address": item["address"] or f"{city_name} (CT)",
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
                    new_in_query += 1
                    logger.info(
                        f"  + [{city_name}] {name} | Tel: {item['phone'] or 'N/D'} | P.IVA: {lead_entry['Partita_IVA'] or 'No'}"
                    )

                if new_in_query > 0:
                    logger.info(f"   -> '{query}': {new_in_query} nuove lead qualificate per {city_name}")
                await asyncio.sleep(0.2)

            if m_idx % 5 == 0 and discovered:
                logger.info(f"Salvataggio intermedio checkpoint ({len(discovered)} nuove lead accumulate)...")
                pd.DataFrame(discovered).to_csv(DATA_DIR / "nuove_lead_scoperte.csv", index=False, encoding="utf-8-sig")

    logger.info(f"\nScansione massiva directory completata! Totale nuove lead uniche trovate: {len(discovered)}")

    if verify_cna and discovered:
        leads_with_web = [lead for lead in discovered if lead.get("Website")]
        logger.info(f"Avvio Fase 2: Verifica siti reali su {len(leads_with_web)} aziende...")
        if leads_with_web:
            try:
                async with aiohttp.ClientSession() as session:
                    async with AsyncWebCrawler() as crawler:
                        for lead in leads_with_web:
                            crawl_res = await fetch_website_intelligence(session, lead["Website"], crawler=crawler)
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
            except Exception as e:
                logger.error(f"Errore fase verifica web: {e}")

        for lead in discovered:
            if not lead.get("Website") and lead.get("Partita_IVA"):
                lead["Stato_CNA"] = "🟡 DA VERIFICARE (P.IVA validata, verifica CNA pendente)"
                lead["Azione_Commerciale_Consigliata"] = "Verificare con Ufficio Soci CNA Catania"

            lead["Pitch_Commerciale_TecnicoLIVE"] = generate_outbound_pitch(
                lead["Company Name"], lead["Nicchia_Target"], lead["Stato_CNA"], lead["City"]
            )

    return pd.DataFrame(discovered)
