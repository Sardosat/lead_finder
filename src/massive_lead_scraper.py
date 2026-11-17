import asyncio
import json
import logging
import re
import urllib.parse
from typing import List, Dict, Any, Set, Optional
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
from crawl4ai import AsyncWebCrawler

from src.config import (
    DATA_DIR, EXCEL_DIR,
    OUTPUT_DASHBOARD_EXCEL, OUTPUT_VERIFICA_CNA_EXCEL, OUTPUT_DISCOVERED_EXCEL,
    OUTPUT_DASHBOARD_CSV, OUTPUT_TARGET_CSV, OUTPUT_ASSOCIATI_CSV,
    OUTPUT_VERIFICA_CNA_CSV, OUTPUT_DISCOVERED_CSV, OUTPUT_OUTBOUND_CSV,
    OUTPUT_CSV_ENRICHED, OUTPUT_RIEPILOGO_CSV
)
from src.piva_validator import clean_piva, validate_piva
from src.website_crawler import crawl_single_site, normalize_url
from src.pipeline import format_phone, export_dashboard_excel
from src.territory_data import CATANIA_MUNICIPALITIES, SEARCH_QUERIES
from src.lead_finder import generate_outbound_pitch, fetch_profile_details, load_known_identifiers

logger = logging.getLogger("massive_scraper")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}


async def scrape_single_page(
    session: aiohttp.ClientSession,
    query: str,
    city_slug: str,
    page: int
) -> List[Dict[str, Any]]:
    """Estrae le schede aziendali da una singola pagina per una query e un comune."""
    page_param = f"/p-{page}" if page > 1 else ""
    url = f"https://www.paginegialle.it/ricerca/{query}/{city_slug}{page_param}"
    
    leads = []
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=12)) as resp:
            if resp.status == 404:
                return []
            if resp.status != 200:
                logger.debug(f"Status {resp.status} per {url}")
                return []
                
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select(".search-itm")
            if not cards:
                return []
                
            for c in cards:
                h2 = c.select_one("h2")
                name = h2.get_text(strip=True) if h2 else ""
                if not name:
                    continue
                
                link_el = c.select_one("a[href*='paginegialle.it/']")
                profile_url = link_el["href"] if link_el else ""
                if profile_url and profile_url.startswith("/"):
                    profile_url = "https://www.paginegialle.it" + profile_url
                
                phone_items = [p.get_text(strip=True) for p in c.select(".search-itm__phone-item") if p.get_text(strip=True)]
                if phone_items:
                    phone = " / ".join(format_phone(p) for p in phone_items)
                else:
                    phone_el = c.select_one(".search-itm__phone, a[href^='tel:']")
                    phone = format_phone(phone_el.get_text(strip=True)) if phone_el else ""
                    
                if not phone:
                    wa_el = c.select_one("a[href*='wa.me']")
                    if wa_el:
                        m = re.search(r"wa\.me/(\+?[0-9]+)", wa_el["href"])
                        if m:
                            phone = format_phone(m.group(1))
                
                addr_el = c.select_one(".search-itm__adr")
                full_address = addr_el.get_text(" ", strip=True) if addr_el else ""
                
                cat_el = c.select_one(".search-itm__category")
                category = cat_el.get_text(strip=True) if cat_el else query.replace("-", " ").capitalize()
                
                leads.append({
                    "name": name,
                    "profile_url": profile_url,
                    "phone": phone,
                    "address": full_address,
                    "category": category,
                })
    except Exception as e:
        logger.debug(f"Errore scraping {url}: {e}")
        
    return leads


async def scrape_all_pages_for_query(
    session: aiohttp.ClientSession,
    query: str,
    city_slug: str,
    max_pages: int = 10
) -> List[Dict[str, Any]]:
    """Itera su tutte le pagine fino a esaurimento (404 o lista vuota)."""
    all_leads = []
    for page in range(1, max_pages + 1):
        leads = await scrape_single_page(session, query, city_slug, page)
        if not leads:
            break
        all_leads.extend(leads)
        if len(leads) < 20:
            break
        await asyncio.sleep(0.3)
    return all_leads


async def run_territory_scan(
    selected_municipalities: Optional[List[Dict[str, str]]] = None,
    verify_cna: bool = True,
    save_callback = None
) -> pd.DataFrame:
    """
    Esegue la scansione esaustiva di tutti i 58 comuni della provincia di Catania
    sulle 12 query verticali senza limiti artificiali.
    """
    municipalities = selected_municipalities or CATANIA_MUNICIPALITIES
    known_pivas, known_domains, known_names = load_known_identifiers()
    logger.info(f"Avvio Scansione Territoriale su {len(municipalities)} comuni | Lead già a sistema: {len(known_names)}")

    discovered: List[Dict[str, Any]] = []
    seen_in_session: Set[str] = set()

    sem = asyncio.Semaphore(5)

    async with aiohttp.ClientSession() as session:
        for m_idx, muni in enumerate(municipalities, 1):
            city_name = muni["name"]
            city_slug = muni["slug"]
            area = muni["area"]
            
            logger.info(f"\n[{m_idx}/{len(municipalities)}] === Scansione Comune: {city_name.upper()} (Area: {area}) ===")
            
            for q_idx, q_item in enumerate(SEARCH_QUERIES, 1):
                query = q_item["query"]
                niche = q_item["niche"]
                
                raw_leads = await scrape_all_pages_for_query(session, query, city_slug)
                if not raw_leads:
                    continue
                    
                new_in_query = 0
                for item in raw_leads:
                    name = item["name"]
                    clean_name = name.lower().strip()
                    
                    if clean_name in known_names or clean_name in seen_in_session:
                        continue
                    seen_in_session.add(clean_name)
                    
                    # Estrazione dettagli profilo
                    profile_url = item.get("profile_url")
                    details = {"piva": None, "website": None, "email": None}
                    if profile_url:
                        details = await fetch_profile_details(session, profile_url)
                        
                    piva = details.get("piva")
                    website = details.get("website")
                    email = details.get("email")
                    
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
                        "Address": item["address"] or f"{city_name} (CT)",
                        "Phone": item["phone"],
                        "Email": email or "",
                        "Website": website or "",
                        "Partita_IVA": f"IT{piva}" if piva else "",
                        "P_IVA_Numerica": piva or "",
                        "Fonte_PIVA": "DIRECTORY_PROFILE" if piva else "NOT_FOUND",
                        "Stato_CNA": "🟡 DA VERIFICARE",
                        "Evidenza_CNA": "",
                        "Azione_Commerciale_Consigliata": "Verificare affiliazione CNA",
                        "Pitch_Commerciale_TecnicoLIVE": "",
                        "Data_Scoperta": pd.Timestamp.now().strftime("%Y-%m-%d"),
                    }
                    
                    discovered.append(lead_entry)
                    new_in_query += 1
                    logger.info(f"  + [{city_name}] {name} | Tel: {item['phone']} | P.IVA: {lead_entry['Partita_IVA'] or 'No'}")
                    
                if new_in_query > 0:
                    logger.info(f"   -> '{query}': {new_in_query} nuove lead qualificate per {city_name}")
                    
                await asyncio.sleep(0.2)
                
            # Salvataggio periodico ogni 5 comuni per non perdere dati
            if m_idx % 5 == 0 and discovered:
                logger.info(f"Salvataggio intermedio checkpoint ({len(discovered)} nuove lead accumulate)...")
                temp_df = pd.DataFrame(discovered)
                temp_df.to_csv(DATA_DIR / "nuove_lead_scoperte.csv", index=False, encoding="utf-8-sig")

    logger.info(f"\nScansione massiva directory completata! Totale nuove lead uniche trovate: {len(discovered)}")

    # Fase 2: Verifica CNA con Crawl4AI sui siti web
    if verify_cna and discovered:
        logger.info("Avvio Fase 2: Scansione Crawl4AI per verificare affiliazione CNA sui siti dei nuovi lead...")
        leads_with_web = [lead for lead in discovered if lead.get("Website")]
        logger.info(f"Aziende con sito web da verificare: {len(leads_with_web)} su {len(discovered)}")
        if leads_with_web:
            try:
                async with AsyncWebCrawler() as crawler:
                    for lead in leads_with_web:
                        try:
                            web = lead.get("Website")
                            crawl_res = await crawl_single_site(crawler, web)
                            if not lead["Partita_IVA"] and crawl_res.get("piva"):
                                lead["Partita_IVA"] = f"IT{crawl_res['piva']}"
                                lead["P_IVA_Numerica"] = crawl_res["piva"]
                                lead["Fonte_PIVA"] = "WEBSITE_CRAWL"
                            
                            if crawl_res.get("cna_affiliato"):
                                lead["Stato_CNA"] = "🟢 ASSOCIATO RILEVATO (Convenzione TecnicoLIVE)"
                                lead["Evidenza_CNA"] = crawl_res.get("cna_dettaglio", "")
                                lead["Azione_Commerciale_Consigliata"] = "Proporre sconto/condizioni convenzione CNA Catania"
                            elif lead["Partita_IVA"]:
                                lead["Stato_CNA"] = "🔵 NON ASSOCIATO (Target Tesseramento CNA)"
                                lead["Azione_Commerciale_Consigliata"] = "Proporre Pacchetto TecnicoLIVE + Tesseramento a CNA Catania"
                        except Exception as e:
                            logger.warning(f"Errore crawl su {lead.get('Website')}: {e}")
            except Exception as e:
                logger.error(f"Errore inizializzazione AsyncWebCrawler: {e}")
                
        # Per tutti gli altri senza sito web ma con P.IVA
        for lead in discovered:
            if not lead.get("Website") and lead.get("Partita_IVA"):
                lead["Stato_CNA"] = "🔵 NON ASSOCIATO (Target Tesseramento CNA)"
                lead["Azione_Commerciale_Consigliata"] = "Proporre Pacchetto TecnicoLIVE + Tesseramento a CNA Catania"
                
            lead["Pitch_Commerciale_TecnicoLIVE"] = generate_outbound_pitch(
                lead["Company Name"], lead["Nicchia_Target"], lead["Stato_CNA"], lead["City"]
            )

    df_new = pd.DataFrame(discovered)
    return df_new

