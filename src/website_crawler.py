import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig

from src.config import CNA_DOMAINS, CNA_KEYWORDS, SUBPAGES_TO_CHECK
from src.normalizers import (
    clean_company_website,
    normalize_email,
    normalize_phone_e164,
)
from src.piva_validator import extract_piva_candidates

logger = logging.getLogger("website_crawler")

_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}


def normalize_url(url: Optional[str]) -> Optional[str]:
    """Normalizza un URL aziendale valido; restituisce None se vuoto o se portale/social."""
    if not url or not isinstance(url, str):
        return None
    cleaned = clean_company_website(url)
    return cleaned or None


def detect_cna_affiliation(html_or_text: str, links: Optional[list] = None) -> Tuple[bool, str]:
    """
    Rileva se nel testo/HTML o nei link compare CNA Catania o CNA.
    Supporta wildcard '*' nelle keyword (es. 'associat* cna', 'iscritt* cna').
    Restituisce (trovato: bool, dettaglio: str).
    """
    if not html_or_text:
        return False, ""

    text_lower = html_or_text.lower()

    if links:
        for link in links:
            href = link.get("href", "") if isinstance(link, dict) else str(link)
            href_lower = href.lower()
            for cna_dom in CNA_DOMAINS:
                if cna_dom in href_lower:
                    return True, f"Link a dominio CNA: {href}"

    for kw in CNA_KEYWORDS:
        pattern = r"\b" + re.escape(kw).replace(r"\*", r"\w*") + r"\b"
        if re.search(pattern, text_lower):
            return True, f"Menzione trovata: '{kw}'"

    return False, ""


def _extract_visible_text_and_contacts(html: str) -> Dict[str, Any]:
    """Estrae testo visibile pulito, link esterni, email e telefoni da HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links = [a.get("href", "") for a in soup.find_all("a", href=True)]
    emails: List[str] = []
    phones: List[str] = []

    for href in links:
        hl = href.strip()
        if hl.lower().startswith("mailto:"):
            em = normalize_email(hl)
            if em and em not in emails:
                emails.append(em)
        elif hl.lower().startswith("tel:"):
            p1, p2 = normalize_phone_e164(hl[4:])
            for p in (p1, *(p2.split(" | ") if p2 else [])):
                if p and p not in phones:
                    phones.append(p)

    # Rimuove tag non testuali prima di estrarre il corpus semantico
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    visible = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()

    return {
        "visible_text": visible,
        "links": links,
        "emails": emails,
        "phones": phones,
    }


async def _aiohttp_fetch_html(session: aiohttp.ClientSession, url: str) -> Tuple[int, str]:
    """Scarica HTML con gestione fallback SSL per piccoli siti artigiani con certificati scaduti."""
    timeout = aiohttp.ClientTimeout(total=8)
    try:
        async with session.get(url, headers=_HTTP_HEADERS, timeout=timeout, allow_redirects=True) as resp:
            if resp.status == 200:
                text = await resp.text(errors="replace")
                return resp.status, text
            return resp.status, ""
    except aiohttp.ClientSSLError:
        try:
            async with session.get(
                url, headers=_HTTP_HEADERS, timeout=timeout, allow_redirects=True, ssl=False
            ) as resp:
                if resp.status == 200:
                    return resp.status, await resp.text(errors="replace")
                return resp.status, ""
        except Exception:
            return 0, ""
    except Exception:
        return 0, ""


async def fetch_website_intelligence(
    session: aiohttp.ClientSession,
    base_url: str,
    crawler: Optional[AsyncWebCrawler] = None,
    max_subpages: int = 3,
) -> Dict[str, Any]:
    """
    Scansiona il sito reale di un'azienda (homepage + sottopagine in SUBPAGES_TO_CHECK):
    - Estrae Partita IVA validata Luhn
    - Rileva affiliazione CNA
    - Estrae testo visibile reale (snippet fino a 6.000 caratteri) per rilevamento marchi/H24/certificazioni
    - Recupera email e telefono E.164 se mancanti
    Usa aiohttp veloce come primario e opzionalmente Crawl4AI come fallback per SPA JS-only.
    """
    clean_base = normalize_url(base_url)
    if not clean_base:
        return {
            "piva": None,
            "cna_affiliato": False,
            "cna_dettaglio": "Nessun sito web aziendale valido",
            "crawl_status": "NO_WEBSITE",
            "piva_source": "NONE",
            "pages_scanned": 0,
            "text_snippet": "",
            "email": "",
            "phone": "",
        }

    found_pivas: List[str] = []
    all_texts: List[str] = []
    all_emails: List[str] = []
    all_phones: List[str] = []
    cna_found = False
    cna_detail = ""
    pages_scanned = 0
    last_status = 0

    # Costruisce lista sottopagine unica usando SUBPAGES_TO_CHECK
    seen_sub = set()
    unique_subpages: List[str] = []
    for sub in SUBPAGES_TO_CHECK:
        norm_sub = sub.strip("/")
        if norm_sub not in seen_sub:
            seen_sub.add(norm_sub)
            unique_subpages.append(norm_sub)

    base_with_slash = clean_base.rstrip("/") + "/"
    targets = [clean_base] + [urljoin(base_with_slash, s) for s in unique_subpages if s][:max_subpages]

    for idx, target_url in enumerate(targets):
        status, html = await _aiohttp_fetch_html(session, target_url)
        if idx == 0:
            last_status = status
        if status != 200 or not html:
            continue

        pages_scanned += 1
        parsed = _extract_visible_text_and_contacts(html)
        visible_text = parsed["visible_text"]
        if visible_text:
            all_texts.append(visible_text)

        for em in parsed["emails"]:
            if em not in all_emails:
                all_emails.append(em)
        for ph in parsed["phones"]:
            if ph not in all_phones:
                all_phones.append(ph)

        pivas = extract_piva_candidates(visible_text + " " + html)
        for p in pivas:
            if p not in found_pivas:
                found_pivas.append(p)

        if not cna_found:
            has_cna, det = detect_cna_affiliation(visible_text + " " + html, parsed["links"])
            if has_cna:
                cna_found = True
                cna_detail = det

        # Se homepage già ricca e abbiamo trovato sia testo sia P.IVA, basta così o al più 1 pagina contatti
        if idx >= 1 and found_pivas and len(" ".join(all_texts)) > 400:
            break

    # Fallback Crawl4AI solo per siti JS-rendered con testo visibile quasi vuoto
    combined_text = " ".join(all_texts).strip()
    if crawler is not None and len(combined_text) < 150:
        try:
            run_cfg = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                page_timeout=15000,
                word_count_threshold=5,
                magic=True,
            )
            res = await asyncio.wait_for(crawler.arun(url=clean_base, config=run_cfg), timeout=18)
            if res and res.success:
                pages_scanned = max(pages_scanned, 1)
                full_content = (res.markdown or "") + " " + (res.html or "")
                md_clean = re.sub(r"\s+", " ", res.markdown or "").strip()
                if md_clean:
                    combined_text = (combined_text + " " + md_clean).strip()
                for p in extract_piva_candidates(full_content):
                    if p not in found_pivas:
                        found_pivas.append(p)
                if not cna_found:
                    links = (
                        (res.links.get("external", []) + res.links.get("internal", []))
                        if hasattr(res, "links") and res.links
                        else []
                    )
                    has_cna, det = detect_cna_affiliation(full_content, links)
                    if has_cna:
                        cna_found = True
                        cna_detail = det
        except Exception as e:
            logger.debug(f"Crawl4AI fallback fallito per {clean_base}: {e}")

    best_piva = found_pivas[0] if found_pivas else None
    crawl_status = (
        "SUCCESS"
        if pages_scanned > 0
        else (f"HTTP_{last_status}" if last_status else "UNREACHABLE")
    )

    return {
        "piva": best_piva,
        "cna_affiliato": cna_found,
        "cna_dettaglio": cna_detail or ("Nessuna evidenza web" if pages_scanned > 0 else "Sito non raggiungibile"),
        "crawl_status": crawl_status,
        "piva_source": "WEBSITE_CRAWL" if best_piva else "NOT_FOUND",
        "pages_scanned": pages_scanned,
        "text_snippet": combined_text[:6000],
        "email": all_emails[0] if all_emails else "",
        "phone": all_phones[0] if all_phones else "",
    }


async def crawl_single_site(crawler: AsyncWebCrawler, base_url: str) -> Dict[str, Any]:
    """Wrapper compatibile con la firma precedente, che usa tutte le SUBPAGES_TO_CHECK."""
    clean_base = normalize_url(base_url)
    if not clean_base:
        return {
            "piva": None,
            "cna_affiliato": False,
            "cna_dettaglio": "Nessun sito web indicato",
            "crawl_status": "NO_WEBSITE",
            "piva_source": "NONE",
            "pages_scanned": 0,
            "text_snippet": "",
            "email": "",
            "phone": "",
        }

    run_cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=20000,
        word_count_threshold=5,
        magic=True,
    )

    found_pivas: List[str] = []
    cna_found = False
    cna_detail = ""
    pages_checked: List[str] = []
    texts: List[str] = []

    seen_sub = set()
    subpages: List[str] = []
    for sub in SUBPAGES_TO_CHECK:
        ns = sub.strip("/")
        if ns not in seen_sub:
            seen_sub.add(ns)
            subpages.append(ns)

    base_with_slash = clean_base.rstrip("/") + "/"
    urls = [clean_base] + [urljoin(base_with_slash, s) for s in subpages if s][:4]

    for idx, target_url in enumerate(urls):
        try:
            res = await crawler.arun(url=target_url, config=run_cfg)
            if res.success:
                pages_checked.append(target_url)
                full_content = (res.markdown or "") + " " + (res.html or "")
                if res.markdown:
                    texts.append(re.sub(r"\s+", " ", res.markdown).strip())
                for p in extract_piva_candidates(full_content):
                    if p not in found_pivas:
                        found_pivas.append(p)
                if not cna_found:
                    links = (
                        (res.links.get("external", []) + res.links.get("internal", []))
                        if hasattr(res, "links") and res.links
                        else []
                    )
                    has_cna, det = detect_cna_affiliation(full_content, links)
                    if has_cna:
                        cna_found = True
                        cna_detail = det
                if idx >= 1 and found_pivas and cna_found:
                    break
        except Exception as e:
            logger.debug(f"Errore crawl {target_url}: {e}")
            continue

    best_piva = found_pivas[0] if found_pivas else None
    return {
        "piva": best_piva,
        "cna_affiliato": cna_found,
        "cna_dettaglio": cna_detail or ("Nessuna evidenza web" if pages_checked else "Sito non raggiungibile"),
        "crawl_status": "SUCCESS" if pages_checked else "ERROR",
        "piva_source": "WEBSITE_CRAWL" if best_piva else "NOT_FOUND",
        "pages_scanned": len(pages_checked),
        "text_snippet": " ".join(texts).strip()[:6000],
        "email": "",
        "phone": "",
    }
