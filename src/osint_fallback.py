import asyncio
import logging
import re
from typing import Any, Dict, Optional

import aiohttp

from src.piva_validator import extract_piva_candidates
from src.website_crawler import detect_cna_affiliation

logger = logging.getLogger("osint_fallback")


async def search_duckduckgo_html(session: aiohttp.ClientSession, query: str) -> str:
    """Esegue una ricerca su DuckDuckGo HTML per estrarre snippet pubblici."""
    url = "https://html.duckduckgo.com/html/"
    data = {"q": query}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    try:
        async with session.post(url, data=data, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception as e:
        logger.warning(f"Errore ricerca OSINT per query '{query}': {e}")
    return ""


def clean_company_name_for_search(name: str) -> str:
    """
    Pulisce il nome dell'azienda rimuovendo sottotitoli di Google Maps,
    separatori (' - ', ' • ', ' | ') e keyword descrittive lunghe.
    """
    if not name:
        return ""
    cleaned = re.split(r"\s*[\-•\|–—]\s*", name)[0].strip()
    cleaned = re.sub(r'["\']', "", cleaned).strip()
    return cleaned


async def osint_find_piva(
    session: aiohttp.ClientSession,
    company_name: str,
    city: str,
    address: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Cerca la Partita IVA per aziende senza sito web o con P.IVA mancante,
    interrogando registri e directory pubbliche via query mirata.
    """
    short_name = clean_company_name_for_search(company_name)
    clean_city = city.strip() if city else "Catania"

    query1 = f'"{short_name}" "{clean_city}" "partita iva"'
    html = await search_duckduckgo_html(session, query1)
    pivas = extract_piva_candidates(html)

    if not pivas:
        await asyncio.sleep(0.5)
        query2 = f"{short_name} {clean_city} P.IVA"
        html2 = await search_duckduckgo_html(session, query2)
        pivas = extract_piva_candidates(html2)
        html += " " + html2

    if not pivas and short_name != company_name:
        await asyncio.sleep(0.5)
        query3 = f"{company_name[:40]} {clean_city} partita iva"
        html3 = await search_duckduckgo_html(session, query3)
        pivas = extract_piva_candidates(html3)
        html += " " + html3

    # Verifica affiliazione CNA tramite regex con supporto wildcard '*'
    cna_found, cna_detail = detect_cna_affiliation(html)
    if cna_found and cna_detail:
        cna_detail = f"OSINT — {cna_detail}"

    if pivas:
        return {
            "piva": pivas[0],
            "piva_source": "OSINT_SEARCH",
            "cna_affiliato": cna_found,
            "cna_dettaglio": cna_detail,
        }

    return {
        "piva": None,
        "piva_source": "NOT_FOUND",
        "cna_affiliato": cna_found,
        "cna_dettaglio": cna_detail,
    }
