"""
normalizers.py — Funzioni centralizzate di igiene, normalizzazione CRM E.164,
filtro portali/social, filtro Anti-Persona GDO e controllo geografico.
"""

import re
import urllib.parse
from typing import Dict, Any, List, Tuple

from src.territory_data import CATANIA_MUNICIPALITIES

PORTAL_DOMAINS = (
    "paginegialle",
    "paginebianche",
    "pgcasa",
    "italiaonline",
    "tuttocitta",
    "virgilio",
    "libero",
    "1240.it",
    "dilei.it",
    "siviaggia.it",
    "quifinanza.it",
    "buonissimo.it",
    "supereva.it",
    "facebook.com",
    "fb.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "wa.me",
    "whatsapp.com",
    "google.",
    "goo.gl",
    "iubenda.com",
    "cookiebot.com",
    "apple.com",
    "play.google.com",
    "w3.org",
    "ufficiocamerale",
    "reportaziende",
    "registroimprese",
    "prontopro",
    "habitissimo",
    "instapro",
    "trustpilot",
    "infobel",
    "kompass",
    "europages",
    "cylex",
    "impresaitalia",
    "azienda-italia",
    "icribis",
)

_GDO_NAME_RE = re.compile(
    r"\b("
    r"kasanova|trony|papino|euronics|mediaworld|mediamarket|"
    r"happy\s*casa|gamelife|unieuro|leroy\s*merlin|bricoman|tecnomat|"
    r"mi\s*store|negozi\s*mercato|maxcasa|expert\s+italia|comet\s+s\.?p\.?a\.?|"
    r"bruno\s+s\.?p\.?a\.?|harley[\s\-]*davidson|decathlon|ikea|esselunga|conad|coop\b|"
    r"eni\s+plenitude|enel\s+energia|flagship\s+store|smitri\s+store"
    r")\b",
    re.IGNORECASE,
)

_NON_TRADE_NAME_RE = re.compile(
    r"\b("
    r"elettrauto|pneumatici|soccorso\s+televisivo|autofficina|carrozzeria|"
    r"videogiochi|casalinghi|supermercato|farmacia|ristorante|pizzeria|albergo|"
    r"concessionari[ao]"
    r")\b",
    re.IGNORECASE,
)

_NON_TRADE_CATEGORY_RE = re.compile(
    r"\b("
    r"autofficine|carrozzerie|automobili|auto\s+electrical\s+service|energy\s+supplier|"
    r"television\s+repair|giardinieri|giardinaggio|videogiochi|casalinghi|"
    r"supermercat|farmaci|ristoranti|alberghi|concessionari[ea]?"
    r")\b",
    re.IGNORECASE,
)

_FOREIGN_KEYWORDS = (
    "malta",
    "gozo",
    "ghajnsielem",
    "xewkija",
    "qormi",
    "naxxar",
    "mellieħa",
    "mellieha",
    "mosta",
    "valletta",
    "sliema",
    "birkirkara",
    "szeged",
)

_STRICT_E164_IT_RE = re.compile(r"^\+39(?:3\d{8,9}|0\d{5,10}|800\d{5,6})$")
_MOBILE_E164_IT_RE = re.compile(r"^\+393\d{8,9}$")
_EMAIL_RE = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")

_MUNICIPALITY_MAP = {m["name"].lower(): m for m in CATANIA_MUNICIPALITIES}
_SLUG_MAP = {m["slug"].lower(): m for m in CATANIA_MUNICIPALITIES}


def is_valid_company_website(url: str) -> bool:
    """Restituisce True solo se l'URL appartiene a un dominio aziendale reale (non portale/social)."""
    if not url or not isinstance(url, str):
        return False
    raw = url.strip()
    if not raw or raw.lower() in ("none", "null", "nan", "n/d"):
        return False
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    try:
        parsed = urllib.parse.urlparse(raw)
        host = parsed.netloc.lower().strip()
        if not host or "." not in host:
            return False
        if host.startswith("www."):
            host = host[4:]
        full_lower = raw.lower()
        for bad in PORTAL_DOMAINS:
            if bad in host or bad in full_lower:
                return False
        return True
    except Exception:
        return False


def clean_company_website(url: str) -> str:
    """Normalizza l'URL aziendale o restituisce stringa vuota se portale/social/invalido."""
    if not is_valid_company_website(url):
        return ""
    raw = url.strip()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    # Rimuove parametri UTM / tracking superflui mantenendo percorso pulito
    parsed = urllib.parse.urlparse(raw)
    clean = urllib.parse.urlunparse((parsed.scheme, parsed.netloc.lower(), parsed.path.rstrip("/"), "", "", ""))
    return clean


def _normalize_single_italian_phone(token: str) -> str:
    """Normalizza un singolo token telefonico italiano in formato E.164 (+39...), oppure ''."""
    if not token:
        return ""
    s = str(token).strip()
    if s.endswith(".0"):
        s = s[:-2]
    # Rimuove spazi, parentesi, trattini, punti
    s = re.sub(r"[\s\.\-\(\)]", "", s)
    if not s:
        return ""

    # Riconosce e rifiuta subito numeri maltesi/esteri espliciti
    if s.startswith("+") and not s.startswith("+39"):
        return ""
    if s.startswith("00") and not s.startswith("0039"):
        return ""
    if re.match(r"^(?:\+?356|00356)", s):
        return ""

    # Rimuove prefisso internazionale italiano
    if s.startswith("+39"):
        national = s[3:]
    elif s.startswith("0039"):
        national = s[4:]
    elif s.startswith("39") and len(s) >= 11 and s[2] in ("0", "3"):
        national = s[2:]
    else:
        national = s

    # Conserva solo cifre
    national = re.sub(r"\D", "", national)
    if not national:
        return ""

    # Se contiene comunque 356 iniziale su 11 cifre maltesi
    if national.startswith("356") and len(national) in (11,):
        return ""

    candidate = f"+39{national}"
    if _STRICT_E164_IT_RE.match(candidate):
        return candidate
    return ""


def normalize_phone_e164(raw: Any) -> Tuple[str, str]:
    """
    Normalizza una stringa telefonica (anche con più numeri separati da '/', ',', '|', ';')
    restituendo (phone_primary_e164, phone_secondary_joined).
    Privilegia un numero cellulare italiano (+393...) come contatto primario per WhatsApp/CRM.
    """
    if raw is None:
        return "", ""
    raw_str = str(raw).strip()
    if not raw_str or raw_str.lower() in ("nan", "none", "null"):
        return "", ""

    parts = [p.strip() for p in re.split(r"[/|;,\n]+", raw_str) if p.strip()]
    # Ricompone prefisso fisso separato da '/' dal numero locale (es. '095/7139656')
    merged_parts: List[str] = []
    i = 0
    while i < len(parts):
        cur_digits = re.sub(r"\D", "", parts[i])
        if (
            i + 1 < len(parts)
            and re.match(r"^0\d{1,3}$", cur_digits)
            and not _normalize_single_italian_phone(parts[i])
        ):
            nxt_digits = re.sub(r"\D", "", parts[i + 1])
            if re.match(r"^[1-9]\d{4,7}$", nxt_digits) and not re.match(r"^3\d{8,9}$", nxt_digits):
                merged_parts.append(cur_digits + nxt_digits)
                i += 2
                continue
        merged_parts.append(parts[i])
        i += 1

    valid_numbers: List[str] = []
    seen = set()
    for part in merged_parts:
        norm = _normalize_single_italian_phone(part)
        if norm and norm not in seen:
            seen.add(norm)
            valid_numbers.append(norm)

    if not valid_numbers:
        return "", ""

    # Ordina privilegiando i cellulari (+393...) prima dei fissi (+390...)
    mobiles = [n for n in valid_numbers if _MOBILE_E164_IT_RE.match(n)]
    others = [n for n in valid_numbers if not _MOBILE_E164_IT_RE.match(n)]
    ordered = mobiles + others

    primary = ordered[0]
    secondary = " | ".join(ordered[1:]) if len(ordered) > 1 else ""
    return primary, secondary


def is_strict_e164_italian(phone: str) -> bool:
    """Verifica che il numero rispetti rigorosamente il formato E.164 italiano."""
    return bool(phone and _STRICT_E164_IT_RE.match(phone.strip()))


def is_mobile_e164(phone: str) -> bool:
    """Verifica se il numero E.164 è un cellulare italiano (+393...)."""
    return bool(phone and _MOBILE_E164_IT_RE.match(phone.strip()))


def normalize_email(raw: Any) -> str:
    """Normalizza e valida un'email aziendale escludendo indirizzi di portali/spam."""
    if not raw:
        return ""
    s = str(raw).strip().lower()
    if s.startswith("mailto:"):
        s = s[7:].split("?")[0].strip()
    if not _EMAIL_RE.match(s):
        return ""
    domain = s.split("@", 1)[1]
    bad_email_domains = (
        "paginegialle",
        "italiaonline",
        "pgcasa",
        "sentry",
        "example.com",
        "wixpress",
    )
    if any(b in domain for b in bad_email_domains):
        return ""
    return s


def is_anti_persona_retail(company_name: str, category: str = "", website: str = "") -> bool:
    """
    Identifica GDO, catene retail e attività non impiantistiche (Anti-Personas da .agents/product-marketing.md).
    Attenzione: preserva ditte legittime come 'Donini Bruno di Donini Dario' o 'Coel Cancelli Automatici'.
    """
    name = (company_name or "").strip()
    cat = (category or "").strip()
    web = (website or "").strip()

    if _GDO_NAME_RE.search(name) or _GDO_NAME_RE.search(web):
        return True
    if _NON_TRADE_NAME_RE.search(name):
        return True
    if cat and _NON_TRADE_CATEGORY_RE.search(cat):
        return True
    # Elettrodomestici generici senza alcun riferimento impiantistico/clima/caldaie
    if cat.lower().strip() == "elettrodomestici" and not re.search(
        r"clima|calda|termo|idraul|condiz|refriger|riscald|assistenza\s+tecnica", name, re.IGNORECASE
    ):
        return True
    return False


def is_maltese_or_foreign_record(row: Dict[str, Any]) -> bool:
    """Verifica se un record appartiene a Malta (+356 / MT) o all'estero."""
    country = str(row.get("Country", "")).strip().upper()
    if country in ("MT", "MALTA", "HU"):
        return True

    raw_phone = re.sub(r"[\s\.\-_]", "", str(row.get("Phone", "")))
    if re.match(r"^(?:\+?356|00356)", raw_phone):
        return True

    text = " ".join(
        str(row.get(col, "")) for col in ("City", "Address", "State", "Company Name")
    ).lower()
    return any(k in text for k in _FOREIGN_KEYWORDS)


def normalize_city_and_area(city: str, address: str = "") -> Tuple[str, str]:
    """Normalizza il nome del comune e mappa l'Area Geografica ufficiale della Città Metropolitana di Catania."""
    raw_city = (city or "").strip()
    addr_lower = (address or "").lower()

    # Riconoscimento esatto da comune noto
    key = raw_city.lower()
    if key in _MUNICIPALITY_MAP:
        m = _MUNICIPALITY_MAP[key]
        return m["name"], m["area"]
    slug_key = key.replace(" ", "-").replace("'", "-")
    if slug_key in _SLUG_MAP:
        m = _SLUG_MAP[slug_key]
        return m["name"], m["area"]

    # Fallback su indirizzo
    for muni in CATANIA_MUNICIPALITIES:
        if muni["name"].lower() in addr_lower:
            return muni["name"], muni["area"]

    clean_name = raw_city.title() if raw_city else "Catania"
    return clean_name, "Area Metropolitana" if clean_name == "Catania" else "Provincia di Catania"
