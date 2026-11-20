"""
Scanner Massivo Territoriale Termoidraulica Catania & Provincia
Estrae tutte le ditte di termoidraulica, caldaie, riscaldamento e idraulica
nei comuni della Città Metropolitana di Catania, arricchendole con il Clay Engine.
"""

import asyncio
import json
import logging
import re
import sys
import urllib.parse
from typing import List, Dict, Any, Set, Optional, Tuple
from pathlib import Path

# Assicura che la root del progetto sia in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import aiohttp
from bs4 import BeautifulSoup
import pandas as pd

from src.config import DATA_DIR, REPORTS_DIR
from src.piva_validator import clean_piva, validate_piva
from src.pipeline import format_phone, is_maltese_or_foreign
from src.territory_data import CATANIA_MUNICIPALITIES
from src.clay_engine import enrich_dataset_with_clay_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("termoidraulica_scanner")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}

# Query mirate strettamente al dominio termoidraulico e riscaldamento
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
    """Carica le lead storiche per evitare duplicati e per arricchimento."""
    known_names = set()
    known_pivas = set()
    known_phones = set()
    df_existing = pd.DataFrame()

    master_path = DATA_DIR / "campagna_outbound_tecnicolive.csv"
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


async def fetch_profile_details(session: aiohttp.ClientSession, profile_url: str) -> Dict[str, Any]:
    """Estrae dettagli aggiuntivi dalla scheda profilo (P.IVA, Sito web, Email)."""
    res = {"piva": None, "website": None, "email": None}
    if not profile_url:
        return res
    try:
        async with session.get(profile_url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            if resp.status == 200:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                # 1. Ricerca P.IVA da JSON-LD
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = json.loads(script.string or "{}")
                        if isinstance(data, dict):
                            vat = data.get("vatID") or data.get("taxID")
                            if vat:
                                cp = clean_piva(str(vat))
                                if cp and validate_piva(cp):
                                    res["piva"] = cp
                                    break
                    except Exception:
                        pass

                # Fallback P.IVA via regex
                if not res["piva"]:
                    m = re.search(r"\b(IT)?([0-9]{11})\b", html)
                    if m:
                        cp = clean_piva(m.group(2))
                        if cp and validate_piva(cp):
                            res["piva"] = cp

                # 2. Sito web esterno
                for a in soup.select("a[href*='http']"):
                    href = a.get("href", "")
                    if "paginegialle.it" not in href and "italiaonline.it" not in href and "facebook.com" not in href and "google." not in href:
                        res["website"] = href.split("?")[0].strip()
                        break

                # 3. Email
                mail_el = soup.select_one("a[href^='mailto:']")
                if mail_el:
                    res["email"] = mail_el["href"].replace("mailto:", "").split("?")[0].strip().lower()
    except Exception as e:
        logger.debug(f"Errore fetch profile {profile_url}: {e}")
    return res


async def scrape_query_for_city(
    session: aiohttp.ClientSession,
    query: str,
    city_slug: str,
    max_pages: int = 5
) -> List[Dict[str, Any]]:
    """Estrae tutte le aziende per una data query e comune."""
    results = []
    for page in range(1, max_pages + 1):
        page_param = f"/p-{page}" if page > 1 else ""
        url = f"https://www.paginegialle.it/ricerca/{query}/{city_slug}{page_param}"
        try:
            async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    break
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select(".search-itm")
                if not cards:
                    break

                for c in cards:
                    h2 = c.select_one("h2")
                    name = h2.get_text(strip=True) if h2 else ""
                    if not name:
                        continue

                    link_el = c.select_one("a[href*='paginegialle.it/']")
                    profile_url = link_el["href"] if link_el else ""
                    if profile_url and profile_url.startswith("/"):
                        profile_url = "https://www.paginegialle.it" + profile_url

                    # Telefono
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
                    address = addr_el.get_text(" ", strip=True) if addr_el else ""

                    cat_el = c.select_one(".search-itm__category")
                    category = cat_el.get_text(strip=True) if cat_el else query.replace("-", " ").capitalize()

                    results.append({
                        "name": name,
                        "profile_url": profile_url,
                        "phone": phone,
                        "address": address,
                        "category": category,
                    })

                if len(cards) < 20:
                    break
                await asyncio.sleep(0.15)
        except Exception as e:
            logger.debug(f"Errore scrape {url}: {e}")
            break
    return results


async def run_termoidraulica_scan(max_municipalities: Optional[int] = None) -> pd.DataFrame:
    """Esegue la scansione provinciale su tutti i comuni o un sottoinsieme."""
    known_names, known_pivas, known_phones, df_existing = load_known_leads()
    logger.info(f"Avvio Scansione Termoidraulica Catania & Provincia | Lead storiche a sistema: {len(known_names)}")

    # Filtra le lead storiche già presenti che appartengono a termoidraulica/HVAC
    existing_termo = pd.DataFrame()
    if not df_existing.empty:
        mask = df_existing["Nicchia_Target"].str.contains("Termoidraulica|HVAC|Caldaie|Clima", case=False, na=False) | \
               df_existing.get("Category", pd.Series([""]*len(df_existing))).str.contains("termoidraulica|caldaie|idraulic|climatiz", case=False, na=False)
        existing_termo = df_existing[mask].copy()
        logger.info(f"Lead di Termoidraulica/HVAC già censite nel database: {len(existing_termo)}")

    municipalities = CATANIA_MUNICIPALITIES[:max_municipalities] if max_municipalities else CATANIA_MUNICIPALITIES
    new_discovered: List[Dict[str, Any]] = []
    seen_in_session: Set[str] = set()

    async with aiohttp.ClientSession() as session:
        for idx, muni in enumerate(municipalities, 1):
            c_name = muni["name"]
            c_slug = muni["slug"]
            area = muni["area"]

            logger.info(f"[{idx}/{len(municipalities)}] Scansione Termoidraulica: {c_name.upper()} ({area})")

            for q_item in TERMO_QUERIES:
                q = q_item["query"]
                niche = q_item["niche"]

                cards = await scrape_query_for_city(session, q, c_slug)
                if not cards:
                    continue

                for item in cards:
                    raw_name = item["name"]
                    c_name_key = raw_name.lower().strip()

                    # Deduplica
                    if c_name_key in known_names or c_name_key in seen_in_session:
                        continue
                    seen_in_session.add(c_name_key)

                    # Dettagli profilo per P.IVA
                    details = await fetch_profile_details(session, item["profile_url"])
                    piva = details.get("piva")
                    website = details.get("website")
                    email = details.get("email")

                    if piva and piva in known_pivas:
                        continue

                    # Verifica CNA su sito web o default non associato
                    stato_cna = "🔵 NON ASSOCIATO (Target Tesseramento CNA)" if piva else "🟡 DA VERIFICARE"
                    azione = "Proporre Pacchetto TecnicoLIVE + Tesseramento a CNA Catania" if piva else "Verificare affiliazione CNA"

                    new_discovered.append({
                        "Company Name": raw_name,
                        "Nicchia_Target": niche,
                        "Category": item["category"],
                        "City": c_name,
                        "Address": item["address"] or f"{c_name} (CT)",
                        "Phone": item["phone"],
                        "Email": email or "",
                        "Website": website or "",
                        "Partita_IVA": f"IT{piva}" if piva else "",
                        "P_IVA_Numerica": piva or "",
                        "Fonte_PIVA": "DIRECTORY_PROFILE" if piva else "NOT_FOUND",
                        "Stato_CNA": stato_cna,
                        "Evidenza_CNA": "",
                        "Azione_Commerciale_Consigliata": azione,
                        "Pitch_Commerciale_TecnicoLIVE": "",
                        "Data_Scoperta": pd.Timestamp.now().strftime("%Y-%m-%d"),
                        "Area_Geografica": area,
                    })

                await asyncio.sleep(0.1)

    logger.info(f"Scansione completata: trovate {len(new_discovered)} NUOVE ditte uniche di termoidraulica.")

    # Unione con le ditte storiche di termoidraulica
    df_new = pd.DataFrame(new_discovered)
    area_map = {m["name"].lower(): m["area"] for m in CATANIA_MUNICIPALITIES}

    if not df_new.empty:
        df_new["Area_Geografica"] = df_new["City"].str.lower().map(area_map).fillna("Area Metropolitana")

    if not existing_termo.empty:
        existing_termo["Area_Geografica"] = existing_termo["City"].str.lower().map(area_map).fillna("Area Metropolitana")

    all_termo = pd.concat([existing_termo, df_new], ignore_index=True)
    all_termo.drop_duplicates(subset=["Company Name", "City"], keep="first", inplace=True)
    all_termo = all_termo[~all_termo.apply(is_maltese_or_foreign, axis=1)].copy()

    logger.info(f"Totale aziende Termoidraulica & Riscaldamento consolidate: {len(all_termo)}")

    # Applica l'arricchimento con il Clay Engine
    enriched_termo = enrich_dataset_with_clay_engine(all_termo)

    # Salva il file dedicato in data/
    out_file = DATA_DIR / "termoidraulica_catania_provincia.csv"
    enriched_termo.to_csv(out_file, index=False, encoding="utf-8-sig")
    logger.info(f"Dataset salvato con successo in {out_file}")

    # Aggiorna anche il file master se ci sono nuove ditte
    if not df_new.empty and not df_existing.empty:
        combined_master = pd.concat([df_existing, df_new], ignore_index=True)
        combined_master.drop_duplicates(subset=["Company Name", "City"], keep="first", inplace=True)
        combined_enriched = enrich_dataset_with_clay_engine(combined_master)
        combined_enriched.to_csv(DATA_DIR / "campagna_outbound_tecnicolive.csv", index=False, encoding="utf-8-sig")
        combined_enriched.to_csv(DATA_DIR / "tutte_le_lead.csv", index=False, encoding="utf-8-sig")
        logger.info(f"Dataset master aggiornato ({len(combined_enriched)} lead totali).")

    return enriched_termo


if __name__ == "__main__":
    asyncio.run(run_termoidraulica_scan())
