"""
tech_audit.py — Livello 1 Enrichment (Basso Costo / Alta Precisione).
Analizza il sito web pubblico dell'azienda per rilevare:
- HTTP status & HTTPS/SSL
- Stack CMS (WordPress, Shopify, Wix, Webflow, PrestaShop, Magento, Joomla, Custom)
- Pixel & Analytics (Meta Pixel, GTM, GA4, TikTok, LinkedIn)
- CTA WhatsApp & Form prenotazione/preventivo
- Link social (Facebook, Instagram, LinkedIn, YouTube, TikTok)
- Email pubbliche (incluse forme offuscate [at]) con separazione rigorosa PEC vs Email ordinaria
- Verifica DNS MX reale via dnspython
- Estrazione P.IVA validate con algoritmo di Luhn
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
import dns.resolver
from bs4 import BeautifulSoup

from engine.compliance.lia_engine import is_pec_email
from engine.schemas.lead import TechAuditData
from src.normalizers import clean_company_website, normalize_email
from src.piva_validator import extract_piva_candidates

logger = logging.getLogger("tech_audit")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}

_AUDIT_SUBPAGES = ("contatti", "chi-siamo", "about", "privacy-policy", "servizi")

_PLAIN_EMAIL_RE = re.compile(r"\b[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}\b", re.IGNORECASE)
_OBFUSCATED_EMAIL_RE = re.compile(
    r"\b([a-z0-9._%+\-]+)\s*(?:\[\s*at\s*\]|\(\s*at\s*\)|\sat\s)\s*([a-z0-9.\-]+)\s*(?:\[\s*dot\s*\]|\(\s*dot\s*\)|\.)\s*([a-z]{2,})\b",
    re.IGNORECASE,
)

_CMS_SIGNATURES = (
    ("Shopify", re.compile(r"cdn\.shopify\.com|myshopify\.com|Shopify\.theme", re.I)),
    ("WordPress", re.compile(r"wp-content/|wp-includes/|content=[\"']WordPress", re.I)),
    ("Wix", re.compile(r"wixstatic\.com|wix\.com/|_wixCIDX", re.I)),
    ("Webflow", re.compile(r"website-files\.com|data-wf-domain|Webflow", re.I)),
    ("Squarespace", re.compile(r"squarespace\.com|static1\.squarespace", re.I)),
    ("PrestaShop", re.compile(r"prestashop|modules/ps_", re.I)),
    ("Magento", re.compile(r"mage/cookies|Magento_", re.I)),
    ("Joomla", re.compile(r"/media/jui/|content=[\"']Joomla!", re.I)),
)

_PIXEL_SIGNATURES = (
    ("Meta Pixel", re.compile(r"connect\.facebook\.net|fbq\s*\(", re.I)),
    ("Google Tag Manager", re.compile(r"googletagmanager\.com/gtm\.js", re.I)),
    ("Google Analytics 4", re.compile(r"googletagmanager\.com/gtag/js|G-[A-Z0-9]{6,}", re.I)),
    ("TikTok Pixel", re.compile(r"analytics\.tiktok\.com|ttq\.load", re.I)),
    ("LinkedIn Insight Tag", re.compile(r"snap\.licdn\.com/li\.lms-analytics", re.I)),
)

_BOOKING_HINT_RE = re.compile(
    r"calendly\.com|cal\.com|booksy\.com|treatwell|fresha\.com|prenota\s+(?:ora|un\s+appuntamento|visita|consulenza)|"
    r"richiedi\s+(?:un\s+)?preventivo|fissa\s+un\s+appuntamento",
    re.I,
)


def _extract_emails_from_text_and_links(text: str, links: List[str]) -> tuple[List[str], str]:
    """Estrae email ordinarie e separa eventuale PEC."""
    ordinary: List[str] = []
    pec = ""
    candidates: List[str] = []

    for href in links:
        if href.lower().startswith("mailto:"):
            candidates.append(href)
    for m in _PLAIN_EMAIL_RE.finditer(text or ""):
        candidates.append(m.group(0))
    for m in _OBFUSCATED_EMAIL_RE.finditer(text or ""):
        candidates.append(f"{m.group(1)}@{m.group(2)}.{m.group(3)}")

    for cand in candidates:
        em = normalize_email(cand)
        if not em:
            continue
        if is_pec_email(em):
            if not pec:
                pec = em
        elif em not in ordinary:
            ordinary.append(em)

    return ordinary, pec


def _detect_social_links(links: List[str]) -> Dict[str, str]:
    socials: Dict[str, str] = {}
    for href in links:
        hl = href.lower().strip()
        if not hl.startswith("http"):
            continue
        if "facebook.com" in hl and "facebook" not in socials:
            socials["facebook"] = href.strip()
        elif "instagram.com" in hl and "instagram" not in socials:
            socials["instagram"] = href.strip()
        elif "linkedin.com" in hl and "linkedin" not in socials:
            socials["linkedin"] = href.strip()
        elif ("youtube.com" in hl or "youtu.be" in hl) and "youtube" not in socials:
            socials["youtube"] = href.strip()
        elif "tiktok.com" in hl and "tiktok" not in socials:
            socials["tiktok"] = href.strip()
    return socials


def audit_html_snapshot(html: str, final_url: str = "", http_status: int = 200) -> TechAuditData:
    """Esegue l'audit tecnico deterministico su uno snapshot HTML già scaricato (testabile offline)."""
    soup = BeautifulSoup(html or "", "html.parser")
    links = [a.get("href", "") for a in soup.find_all("a", href=True)]

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    visible_text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()

    cms = "Custom/HTML"
    for name, pat in _CMS_SIGNATURES:
        if pat.search(html or ""):
            cms = name
            break

    pixels = [name for name, pat in _PIXEL_SIGNATURES if pat.search(html or "")]
    has_wa = bool(
        re.search(r"wa\.me/|api\.whatsapp\.com|whatsapp://", html or "", re.I)
        or any("wa.me" in l.lower() or "whatsapp" in l.lower() for l in links)
    )
    has_booking = bool(_BOOKING_HINT_RE.search(html or "") or (soup.find("form") and re.search(r"preventiv|prenot|appuntament|contatt", visible_text, re.I)))

    emails, pec = _extract_emails_from_text_and_links(visible_text + " " + (html or ""), links)
    pivas = extract_piva_candidates(visible_text + " " + (html or ""))
    socials = _detect_social_links(links)

    return TechAuditData(
        http_status=http_status,
        has_ssl=final_url.lower().startswith("https://"),
        cms_stack=cms,
        tracking_pixels=pixels,
        has_whatsapp_cta=has_wa,
        has_booking_or_quote_form=has_booking,
        social_links=socials,
        emails_found=emails,
        pec_found=pec,
        pivas_found=pivas,
        text_snippet=visible_text[:6000],
    )


def check_domain_mx(email_or_domain: str) -> bool:
    """Verifica reale del record DNS MX per il dominio email (evita bounce)."""
    val = (email_or_domain or "").strip().lower()
    if not val:
        return False
    domain = val.split("@", 1)[1] if "@" in val else urlparse(val if "://" in val else f"https://{val}").netloc
    domain = domain.split(":")[0].strip()
    if not domain or "." not in domain:
        return False
    try:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 4.0
        answers = resolver.resolve(domain, "MX")
        return len(answers) > 0
    except Exception:
        return False


class TechAuditor:
    """Esecutore asincrono Livello 1 (Tech Audit + MX Check) con cache DNS."""

    def __init__(self):
        self._mx_cache: Dict[str, bool] = {}

    async def verify_email_mx(self, email: str) -> bool:
        if not email or "@" not in email:
            return False
        domain = email.strip().lower().split("@", 1)[1]
        if domain not in self._mx_cache:
            self._mx_cache[domain] = await asyncio.to_thread(check_domain_mx, domain)
        return self._mx_cache[domain]

    async def _fetch_page(self, session: aiohttp.ClientSession, url: str) -> tuple[int, str, str]:
        timeout = aiohttp.ClientTimeout(total=8)
        try:
            async with session.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=True) as resp:
                if resp.status == 200:
                    return resp.status, str(resp.url), await resp.text(errors="replace")
                return resp.status, str(resp.url), ""
        except aiohttp.ClientSSLError:
            try:
                async with session.get(
                    url, headers=_HEADERS, timeout=timeout, allow_redirects=True, ssl=False
                ) as resp:
                    if resp.status == 200:
                        return resp.status, str(resp.url), await resp.text(errors="replace")
                    return resp.status, str(resp.url), ""
            except Exception:
                return 0, url, ""
        except Exception:
            return 0, url, ""

    async def audit_website(
        self,
        website: str,
        session: Optional[aiohttp.ClientSession] = None,
        check_mx: bool = True,
    ) -> TechAuditData:
        clean_url = clean_company_website(website)
        if not clean_url:
            return TechAuditData()

        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()

        try:
            status, final_url, html = await self._fetch_page(session, clean_url)
            if status != 200 or not html:
                return TechAuditData(http_status=status, has_ssl=clean_url.startswith("https://"))

            combined = audit_html_snapshot(html, final_url=final_url, http_status=status)

            # Controlla sottopagine ad alta densità (contatti, chi-siamo, privacy) se mancano email o P.IVA
            base_slash = final_url.rstrip("/") + "/"
            for sub in _AUDIT_SUBPAGES[:3]:
                if combined.emails_found and combined.pivas_found:
                    break
                sub_status, sub_final, sub_html = await self._fetch_page(session, urljoin(base_slash, sub))
                if sub_status == 200 and sub_html:
                    sub_audit = audit_html_snapshot(sub_html, final_url=sub_final, http_status=sub_status)
                    for em in sub_audit.emails_found:
                        if em not in combined.emails_found:
                            combined.emails_found.append(em)
                    if not combined.pec_found and sub_audit.pec_found:
                        combined.pec_found = sub_audit.pec_found
                    for pv in sub_audit.pivas_found:
                        if pv not in combined.pivas_found:
                            combined.pivas_found.append(pv)
                    if not combined.has_whatsapp_cta and sub_audit.has_whatsapp_cta:
                        combined.has_whatsapp_cta = True
                    if not combined.has_booking_or_quote_form and sub_audit.has_booking_or_quote_form:
                        combined.has_booking_or_quote_form = True
                    for k, v in sub_audit.social_links.items():
                        combined.social_links.setdefault(k, v)
                    if sub_audit.text_snippet and len(combined.text_snippet) < 6000:
                        combined.text_snippet = (combined.text_snippet + " " + sub_audit.text_snippet)[:6000]

            if check_mx and combined.emails_found:
                combined.email_mx_valid = await self.verify_email_mx(combined.emails_found[0])

            return combined
        finally:
            if own_session:
                await session.close()
