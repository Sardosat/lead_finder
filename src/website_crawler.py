import asyncio
import logging
import re
from urllib.parse import urljoin, urlparse
from typing import Optional, Dict, Any, Tuple

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode
from src.config import CNA_KEYWORDS, CNA_DOMAINS, SUBPAGES_TO_CHECK
from src.piva_validator import extract_piva_candidates

logger = logging.getLogger("website_crawler")


def normalize_url(url: Optional[str]) -> Optional[str]:
    """Assicura schema https:// e rimuove spazi o frammenti."""
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if not url or url.lower() in ("none", "null", "nan", ""):
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def detect_cna_affiliation(html_or_text: str, links: Optional[list] = None) -> Tuple[bool, str]:
    """
    Rileva se nel testo/HTML o nei link compare CNA Catania o CNA.
    Restituisce (trovato: bool, dettaglio: str).
    """
    if not html_or_text:
        return False, ""
    
    text_lower = html_or_text.lower()
    
    # 1. Verifica link in uscita verso domini CNA
    if links:
        for link in links:
            href = link.get("href", "") if isinstance(link, dict) else str(link)
            for cna_dom in CNA_DOMAINS:
                if cna_dom in href.lower():
                    return True, f"Link a dominio CNA: {href}"
    
    # 2. Controllo keyword specifiche
    for kw in CNA_KEYWORDS:
        # Regex per match esatto parola
        pattern = r"\b" + re.escape(kw).replace(r"\*", r"\w*") + r"\b"
        if re.search(pattern, text_lower):
            return True, f"Menzione trovata: '{kw}'"
            
    return False, ""


async def crawl_single_site(crawler: AsyncWebCrawler, base_url: str) -> Dict[str, Any]:
    """
    Esegue il crawl del sito web di una lead per:
    1. Estrarre e validare la Partita IVA (homepage -> contatti/privacy).
    2. Identificare eventuali badge/link di affiliazione a CNA Catania.
    """
    clean_base = normalize_url(base_url)
    if not clean_base:
        return {
            "piva": None,
            "cna_affiliato": False,
            "cna_dettaglio": "Nessun sito web indicato",
            "crawl_status": "NO_WEBSITE",
            "piva_source": "NONE",
        }
    
    run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=20000,
        word_count_threshold=5,
        magic=True,
    )

    found_pivas = []
    cna_found = False
    cna_detail = ""
    pages_checked = []

    # Prova prima l'homepage
    try:
        res = await crawler.arun(url=clean_base, config=run_cfg)
        pages_checked.append(clean_base)
        
        if res.success:
            full_content = (res.markdown or "") + " " + (res.html or "")
            pivas = extract_piva_candidates(full_content)
            if pivas:
                found_pivas.extend(pivas)
            
            # Controllo link estratti
            links = res.links.get("external", []) + res.links.get("internal", []) if hasattr(res, "links") and res.links else []
            has_cna, det = detect_cna_affiliation(full_content, links)
            if has_cna:
                cna_found = True
                cna_detail = det
        else:
            logger.warning(f"Crawl homepage fallito per {clean_base}: {res.error_message}")
    except Exception as e:
        logger.warning(f"Errore crawl homepage {clean_base}: {e}")

    # Se non abbiamo trovato la P.IVA o vogliamo cercare sezioni legali/contatti
    if not found_pivas:
        subpages_to_try = ["contatti", "privacy-policy", "chi-siamo"]
        for sub in subpages_to_try:
            sub_url = urljoin(clean_base + ("/" if not clean_base.endswith("/") else ""), sub)
            try:
                sub_res = await crawler.arun(url=sub_url, config=run_cfg)
                if sub_res.success:
                    pages_checked.append(sub_url)
                    full_content = (sub_res.markdown or "") + " " + (sub_res.html or "")
                    pivas = extract_piva_candidates(full_content)
                    if pivas:
                        found_pivas.extend(pivas)
                    
                    if not cna_found:
                        links = sub_res.links.get("external", []) if hasattr(sub_res, "links") and sub_res.links else []
                        has_cna, det = detect_cna_affiliation(full_content, links)
                        if has_cna:
                            cna_found = True
                            cna_detail = det
                            
                    if found_pivas:
                        break
            except Exception:
                continue

    best_piva = found_pivas[0] if found_pivas else None
    
    return {
        "piva": best_piva,
        "cna_affiliato": cna_found,
        "cna_dettaglio": cna_detail or ("Nessuna evidenza web" if pages_checked else "Sito non raggiungibile"),
        "crawl_status": "SUCCESS" if pages_checked else "ERROR",
        "piva_source": "WEBSITE_CRAWL" if best_piva else "NOT_FOUND",
        "pages_scanned": len(pages_checked),
    }

