import asyncio
import json
import logging
import re
import urllib.parse
from typing import List, Dict, Any, Set, Optional, Tuple
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
from src.pipeline import format_phone, export_dashboard_excel, is_maltese_or_foreign

logger = logging.getLogger("lead_finder")

# Principali comuni della Città Metropolitana di Catania da scandagliare
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

# Query di ricerca per i 4 settori chiave
BASE_QUERIES = [
    {"query": "climatizzatori", "niche": "HVAC & Climatizzazione"},
    {"query": "caldaie", "niche": "HVAC & Climatizzazione"},
    {"query": "termoidraulica", "niche": "Termoidraulica & Idraulica"},
    {"query": "idraulici", "niche": "Termoidraulica & Idraulica"},
    {"query": "elettricisti", "niche": "Impianti Elettrici"},
    {"query": "impianti-elettrici", "niche": "Impianti Elettrici"},
    {"query": "impianti-industriali", "niche": "Impiantistica Generale"},
]

SEARCH_SECTORS = [
    {**q, "city": "catania"} for q in BASE_QUERIES
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}


def load_known_identifiers() -> Tuple[Set[str], Set[str], Set[str]]:
    """Carica P.IVA, domini web e nomi di aziende già presenti nel dataset per non duplicare."""
    known_pivas = set()
    known_domains = set()
    known_names = set()

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
    """
    Scarica la scheda aziendale per estrarre:
    - Partita IVA ufficiale (vatID da JSON-LD)
    - Sito web esterno reale (non PagineGialle)
    - Email se presente
    """
    res = {
        "piva": None,
        "website": None,
        "email": None,
    }
    try:
        async with session.get(profile_url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return res
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            
            # 1. Analisi JSON-LD
            for s in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(s.string)
                    if isinstance(data, dict):
                        vat = data.get("vatID") or data.get("taxID")
                        if vat:
                            cleaned = clean_piva(str(vat))
                            if cleaned and validate_piva(cleaned):
                                res["piva"] = cleaned
                                
                        # Controllo contatti
                        cp = data.get("contactPoint")
                        if isinstance(cp, list) and cp:
                            em = cp[0].get("email")
                            if em:
                                res["email"] = em
                except Exception:
                    pass

            # 2. Ricerca sito web esterno dell'azienda (esclusi portali e directory)
            blacklist_domains = [
                "paginegialle", "italiaonline", "pgcasa", "tuttocitta", "virgilio", "libero",
                "facebook", "wa.me", "linkedin", "1240.it", "dilei.it", "siviaggia.it",
                "quifinanza.it", "buonissimo.it", "supereva.it", "google", "instagram"
            ]
            for a in soup.find_all("a", href=True):
                h = a["href"].strip()
                if h.startswith("http") and not any(skip in h.lower() for skip in blacklist_domains):
                    res["website"] = h
                    break
    except Exception as e:
        logger.debug(f"Errore lettura profilo {profile_url}: {e}")
        
    return res


async def scrape_directory_listing(
    session: aiohttp.ClientSession,
    query: str,
    city: str,
    page: int = 1
) -> List[Dict[str, Any]]:
    """Estrae l'elenco delle schede aziendali da PagineGialle."""
    page_param = f"/p-{page}" if page > 1 else ""
    url = f"https://www.paginegialle.it/ricerca/{query}/{city}{page_param}"
    
    leads = []
    try:
        async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=12)) as resp:
            if resp.status != 200:
                return leads
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")
            
            cards = soup.select(".search-itm")
            for c in cards:
                h2 = c.select_one("h2")
                name = h2.get_text(strip=True) if h2 else ""
                if not name:
                    continue
                
                # Link profilo interno
                link_el = c.select_one("a[href*='paginegialle.it/']")
                profile_url = link_el["href"] if link_el else ""
                if profile_url and profile_url.startswith("/"):
                    profile_url = "https://www.paginegialle.it" + profile_url
                
                # Telefono (gestisce numeri multipli separati)
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
                
                # Indirizzo e Comune
                addr_el = c.select_one(".search-itm__adr")
                full_address = addr_el.get_text(" ", strip=True) if addr_el else ""
                
                # Categoria
                cat_el = c.select_one(".search-itm__category")
                category = cat_el.get_text(strip=True) if cat_el else query.capitalize()
                
                leads.append({
                    "name": name,
                    "profile_url": profile_url,
                    "phone": format_phone(phone),
                    "address": full_address,
                    "category": category,
                })
    except Exception as e:
        logger.warning(f"Errore scraping lista {url}: {e}")
        
    return leads


def generate_outbound_pitch(comp_name: str, niche: str, stato_cna: str, city: str) -> str:
    """Genera l'aggancio verbale personalizzato per il primo contatto (telefono o WhatsApp)."""
    if "ASSOCIATO RILEVATO" in stato_cna:
        return (
            f"Buongiorno {comp_name}, vi contattiamo da TecnicoLIVE. "
            f"In quanto azienda di {niche} operante a {city} e collegata a CNA Catania, "
            f"avete diritto immediato all'assistente vocale AI con lo sconto convenzione per non perdere chiamate mentre i tecnici sono in cantiere."
        )
    else:
        return (
            f"Buongiorno {comp_name}, vi contattiamo da TecnicoLIVE. "
            f"Stiamo supportando le aziende di {niche} a {city} con la convenzione ufficiale CNA Catania: "
            f"attiviamo l'assistente vocale per recuperare gli interventi persi e sblocchiamo il tesseramento CNA con una scontistica dedicata sulla quota d'iscrizione del primo anno."
        )


async def discover_new_leads(
    max_leads_per_sector: int = 15,
    verify_with_crawl4ai: bool = True,
    target_city: Optional[str] = None,
    all_cities: bool = False
) -> pd.DataFrame:
    """
    Cerca nuove lead nei settori chiave, estrae P.IVA, sito web,
    deduplica rispetto al database e verifica affiliazione CNA Catania.
    """
    known_pivas, known_domains, known_names = load_known_identifiers()
    logger.info(f"Filtro deduplica attivo: {len(known_pivas)} P.IVA, {len(known_domains)} domini, {len(known_names)} nomi noti")

    discovered: List[Dict[str, Any]] = []
    seen_in_session: Set[str] = set()

    # Determinazione città da scandagliare
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
                raw_items = await scrape_directory_listing(session, query, city, page=1)
                
                # Se pochi risultati, prova pagina 2
                if len(raw_items) < 8:
                    raw_items += await scrape_directory_listing(session, query, city, page=2)
                    
                collected_for_sector = 0
                for item in raw_items:
                    if collected_for_sector >= max_leads_per_sector:
                        break
                        
                    name = item["name"]
                    clean_name = name.lower().strip()
                    
                    if clean_name in known_names or clean_name in seen_in_session:
                        continue
                    seen_in_session.add(clean_name)
                    
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
                            
                    comune = city.replace("-", " ").title()
                    addr = item["address"]
                    for c_cand in ["Acireale", "Misterbianco", "Mascalucia", "Giarre", "Paternò", "Caltagirone", "Belpasso", "Aci Castello", "San Giovanni La Punta"]:
                        if c_cand.lower() in addr.lower():
                            comune = c_cand
                            break
                            
                    lead_entry = {
                        "Company Name": name,
                        "Nicchia_Target": niche,
                        "Category": item["category"],
                        "City": comune,
                        "Address": item["address"],
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
                    collected_for_sector += 1
                    logger.info(f"  + Trovata NUOVA Lead: {name} ({comune}) | Tel: {item['phone']} | P.IVA: {lead_entry['Partita_IVA'] or 'No'}")
                    await asyncio.sleep(0.3)

    logger.info(f"Totale nuove lead uniche trovate: {len(discovered)}")

    # 3. Verifica con Crawl4AI sui siti web dei nuovi lead scoperti
    if verify_with_crawl4ai and discovered:
        logger.info("Avvio scansione Crawl4AI per verificare affiliazione CNA sui siti dei nuovi lead...")
        async with AsyncWebCrawler() as crawler:
            for lead in discovered:
                web = lead.get("Website")
                if web:
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
                else:
                    if lead["Partita_IVA"]:
                        lead["Stato_CNA"] = "🔵 NON ASSOCIATO (Target Tesseramento CNA)"
                        lead["Azione_Commerciale_Consigliata"] = "Proporre Pacchetto TecnicoLIVE + Tesseramento a CNA Catania"
                
                # Assegna pitch personalizzato
                lead["Pitch_Commerciale_TecnicoLIVE"] = generate_outbound_pitch(
                    lead["Company Name"], lead["Nicchia_Target"], lead["Stato_CNA"], lead["City"]
                )

    df_new = pd.DataFrame(discovered)
    return df_new


def save_discovered_leads(df_new: pd.DataFrame):
    """Salva le nuove lead in formato CSV ed Excel dedicati e le accoda al database master."""
    if df_new.empty:
        logger.info("Nessuna nuova lead da salvare.")
        return

    # Filtro anti-Malta / anti-estero
    df_new = df_new[~df_new.apply(is_maltese_or_foreign, axis=1)].copy()

    # 1. Esportazione CSV per apertura immediata nell'editor (in data/)
    df_new.to_csv(OUTPUT_DISCOVERED_CSV, index=False, encoding="utf-8-sig")
    target_new = df_new[df_new["Stato_CNA"].str.contains("NON ASSOCIATO", na=False)]
    target_new.to_csv(DATA_DIR / "target_cna_nuovi.csv", index=False, encoding="utf-8-sig")

    # 2. Esportazione Excel nella cartella dedicata exports_excel/
    with pd.ExcelWriter(OUTPUT_DISCOVERED_EXCEL, engine="openpyxl") as writer:
        df_new.to_excel(writer, sheet_name="Nuove Lead Scoperte", index=False)
        target_new.to_excel(writer, sheet_name="Target CNA Nuovi", index=False)

    logger.info(f"Nuove lead salvate in CSV ({OUTPUT_DISCOVERED_CSV}) ed Excel ({OUTPUT_DISCOVERED_EXCEL})")

    # 3. Aggiorna anche il database unificato master
    if OUTPUT_CSV_ENRICHED.exists():
        existing_df = pd.read_csv(OUTPUT_CSV_ENRICHED, dtype=str).fillna("")
        # Rimuove eventuali vecchie contaminazioni maltesi
        existing_df = existing_df[~existing_df.apply(is_maltese_or_foreign, axis=1)].copy()
        
        combined_df = pd.concat([existing_df, df_new], ignore_index=True)
        combined_df.drop_duplicates(subset=["Company Name", "City"], keep="first", inplace=True)
        
        # Genera il file per campagna outbound
        if "Pitch_Commerciale_TecnicoLIVE" not in combined_df.columns:
            combined_df["Pitch_Commerciale_TecnicoLIVE"] = ""
            
        for idx, r in combined_df.iterrows():
            if not r.get("Pitch_Commerciale_TecnicoLIVE"):
                combined_df.at[idx, "Pitch_Commerciale_TecnicoLIVE"] = generate_outbound_pitch(
                    r.get("Company Name", ""), r.get("Nicchia_Target", ""), r.get("Stato_CNA", ""), r.get("City", "Catania")
                )
                
        outbound_df = combined_df[[
            "Company Name", "Nicchia_Target", "City", "Phone", "Partita_IVA", "Stato_CNA", "Pitch_Commerciale_TecnicoLIVE"
        ]].copy()
        outbound_df.to_csv(OUTPUT_OUTBOUND_CSV, index=False, encoding="utf-8-sig")

        export_dashboard_excel(combined_df)
        logger.info(f"Database master decontaminato e aggiornato ({len(combined_df)} lead totali)!")
