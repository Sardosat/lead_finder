"""
paginegialle_client.py — Client asincrono unificato per lo scraping di PagineGialle.it.
Sostituisce la logica duplicata in lead_finder.py, massive_lead_scraper.py e termoidraulica_scanner.py.
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from src.normalizers import (
    clean_company_website,
    is_anti_persona_retail,
    normalize_email,
    normalize_phone_e164,
)
from src.piva_validator import clean_piva, extract_piva_candidates, validate_piva

logger = logging.getLogger("paginegialle_client")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}


def _extract_labeled_piva_from_soup(soup: BeautifulSoup) -> Optional[str]:
    """
    Estrae la Partita IVA solo da JSON-LD strutturato o da blocchi etichettati
    esplicitamente ('P.IVA', 'Partita IVA', 'C.F./P.IVA'), mai via regex cieca sull'intero HTML.
    """
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            raw_json = script.string or script.get_text() or ""
            if not raw_json.strip():
                continue
            data = json.loads(raw_json)
            items = data if isinstance(data, list) else [data]
            for obj in items:
                if not isinstance(obj, dict):
                    continue
                vat = obj.get("vatID") or obj.get("taxID")
                if vat:
                    cleaned = clean_piva(str(vat))
                    if cleaned and validate_piva(cleaned):
                        return cleaned
        except Exception:
            continue

    # Cerca nel testo visibile solo vicino a etichette esplicite
    visible_text = soup.get_text(" ", strip=True)
    labeled_matches = re.finditer(
        r"(?:P\.?\s*IVA|PARTITA\s+IVA|P\.\s*I\.|C\.F\.?\s*/\s*P\.?\s*IVA)[\s\:\.\-_]*(?:IT[\s\.\-_]*)?([0-9]{11})\b",
        visible_text,
        flags=re.IGNORECASE,
    )
    for m in labeled_matches:
        cleaned = clean_piva(m.group(1))
        if cleaned and validate_piva(cleaned):
            # Esclude P.IVA nota di Italiaonline/PagineGialle se presente nel footer
            if cleaned not in ("03970540963", "00798870879"):
                return cleaned
    return None


async def fetch_profile_details(
    session: aiohttp.ClientSession,
    profile_url: str,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> Dict[str, Any]:
    """
    Scarica la scheda aziendale PagineGialle per estrarre P.IVA certificata,
    sito web reale (esclusi portali/social) ed email normalizzata.
    """
    res: Dict[str, Any] = {"piva": None, "website": None, "email": None}
    if not profile_url:
        return res

    async def _do_fetch() -> Dict[str, Any]:
        try:
            async with session.get(
                profile_url, headers=DEFAULT_HEADERS, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return res
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                res["piva"] = _extract_labeled_piva_from_soup(soup)

                # Email da JSON-LD o link mailto
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        data = json.loads(script.string or "{}")
                        if isinstance(data, dict):
                            cp = data.get("contactPoint")
                            if isinstance(cp, list) and cp:
                                em = normalize_email(cp[0].get("email"))
                                if em:
                                    res["email"] = em
                                    break
                    except Exception:
                        pass

                if not res["email"]:
                    mail_el = soup.select_one("a[href^='mailto:']")
                    if mail_el:
                        em = normalize_email(mail_el.get("href", ""))
                        if em:
                            res["email"] = em

                # Sito web esterno reale (filtrato da blacklist portali/social)
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    clean_web = clean_company_website(href)
                    if clean_web:
                        res["website"] = clean_web
                        break
        except Exception as e:
            logger.debug(f"Errore lettura profilo {profile_url}: {e}")
        return res

    if semaphore:
        async with semaphore:
            return await _do_fetch()
    return await _do_fetch()


async def scrape_listing_page(
    session: aiohttp.ClientSession,
    query: str,
    city_slug: str,
    page: int = 1,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> List[Dict[str, Any]]:
    """Estrae le schede aziendali da una pagina PagineGialle applicando filtri anti-GDO ed E.164."""
    page_param = f"/p-{page}" if page > 1 else ""
    url = f"https://www.paginegialle.it/ricerca/{query}/{city_slug}{page_param}"
    leads: List[Dict[str, Any]] = []

    async def _do_scrape() -> List[Dict[str, Any]]:
        try:
            async with session.get(
                url, headers=DEFAULT_HEADERS, timeout=aiohttp.ClientTimeout(total=12)
            ) as resp:
                if resp.status == 404 or resp.status != 200:
                    return leads
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                cards = soup.select(".search-itm")
                if not cards:
                    return leads

                for c in cards:
                    h2 = c.select_one("h2")
                    name = h2.get_text(strip=True) if h2 else ""
                    if not name:
                        continue

                    cat_el = c.select_one(".search-itm__category")
                    category = cat_el.get_text(strip=True) if cat_el else query.replace("-", " ").capitalize()

                    if is_anti_persona_retail(name, category):
                        continue

                    link_el = c.select_one("a[href*='paginegialle.it/']")
                    profile_url = link_el["href"] if link_el else ""
                    if profile_url and profile_url.startswith("/"):
                        profile_url = "https://www.paginegialle.it" + profile_url

                    raw_phones: List[str] = [
                        p.get_text(strip=True)
                        for p in c.select(".search-itm__phone-item")
                        if p.get_text(strip=True)
                    ]
                    if not raw_phones:
                        phone_el = c.select_one(".search-itm__phone, a[href^='tel:']")
                        if phone_el:
                            raw_phones.append(phone_el.get_text(strip=True))
                    if not raw_phones:
                        wa_el = c.select_one("a[href*='wa.me']")
                        if wa_el and wa_el.get("href"):
                            m = re.search(r"wa\.me/(\+?[0-9]+)", wa_el["href"])
                            if m:
                                raw_phones.append(m.group(1))

                    phone_primary, phone_secondary = normalize_phone_e164("/".join(raw_phones))

                    addr_el = c.select_one(".search-itm__adr")
                    full_address = addr_el.get_text(" ", strip=True) if addr_el else ""

                    leads.append(
                        {
                            "name": name,
                            "profile_url": profile_url,
                            "phone": phone_primary,
                            "phone_secondary": phone_secondary,
                            "address": full_address,
                            "category": category,
                        }
                    )
        except Exception as e:
            logger.debug(f"Errore scraping lista {url}: {e}")
        return leads

    if semaphore:
        async with semaphore:
            return await _do_scrape()
    return await _do_scrape()


async def scrape_all_pages(
    session: aiohttp.ClientSession,
    query: str,
    city_slug: str,
    max_pages: int = 10,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> List[Dict[str, Any]]:
    """Itera sulle pagine di ricerca fino a esaurimento risultati o limite max_pages."""
    all_leads: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        leads = await scrape_listing_page(session, query, city_slug, page=page, semaphore=semaphore)
        if not leads:
            break
        all_leads.extend(leads)
        if len(leads) < 20:
            break
        await asyncio.sleep(0.25)
    return all_leads
