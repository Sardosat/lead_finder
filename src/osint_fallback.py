import asyncio
import logging
import re
import urllib.parse
import aiohttp
from typing import Optional, Dict, Any, Tuple

from src.piva_validator import extract_piva_candidates
from src.config import CNA_KEYWORDS

logger = logging.getLogger("osint_fallback")


async def search_duckduckgo_html(session: aiohttp.ClientSession, query: str) -> str:
    """Esegue una ricerca su DuckDuckGo HTML per estrarre snippet pubblici."""
    url = "https://html.duckduckgo.com/html/"
    data = {"q": query}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
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
    Es: 'Energetica Clima - Impianti di Climatizzazione...' -> 'Energetica Clima'
    """
    if not name:
        return ""
    # Taglia al primo separatore comune
    cleaned = re.split(r'\s*[\-•\|–—]\s*', name)[0].strip()
    # Rimuove apici e caratteri speciali
    cleaned = re.sub(r'["\']', '', cleaned).strip()
    return cleaned


async def osint_find_piva(
    session: aiohttp.ClientSession,
    company_name: str,
    city: str,
    address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Cerca la Partita IVA per aziende senza sito web o con P.IVA mancante,
    interrogando registri e directory pubbliche via query mirata.
    """
    short_name = clean_company_name_for_search(company_name)
    clean_city = city.strip() if city else "Catania"
    
    # Query 1: Nome breve + Città + 'partita iva'
    query1 = f'"{short_name}" "{clean_city}" "partita iva"'
    html = await search_duckduckgo_html(session, query1)
    pivas = extract_piva_candidates(html)
    
    # Query 2 (fallback): se non trovata, prova senza virgolette strette
    if not pivas:
        await asyncio.sleep(0.5)
        query2 = f'{short_name} {clean_city} P.IVA'
        html2 = await search_duckduckgo_html(session, query2)
        pivas = extract_piva_candidates(html2)
        html += " " + html2
        
    # Query 3 (fallback): con il nome originale intero se diverso
    if not pivas and short_name != company_name:
        await asyncio.sleep(0.5)
        query3 = f'{company_name[:40]} {clean_city} partita iva'
        html3 = await search_duckduckgo_html(session, query3)
        pivas = extract_piva_candidates(html3)
        html += " " + html3
    
    # Verifica anche se nei risultati compare CNA
    cna_found = False
    cna_detail = ""
    html_lower = html.lower()
    for kw in CNA_KEYWORDS:
        if kw in html_lower:
            cna_found = True
            cna_detail = f"Menzione in risultati pubblici: '{kw}'"
            break
            
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

