"""
product_router.py — Router automatico multi-prodotto dell'ecosistema:
1. monetizelab.online -> Marketing Agency, Web Agency, Content Creator
2. tecnicolive.it -> Termoidraulici, Elettricisti, Caldaisti, Installatori Impianti
3. rsksystem.com -> PMI B2B/B2C generiche (CRM, automazioni WhatsApp/Email, Smart Lists)
"""

import re
from typing import Any, Dict, Optional

from engine.schemas.campaign import UpsellProduct

PRODUCT_CATALOG: Dict[UpsellProduct, Dict[str, str]] = {
    "monetizelab": {
        "key": "monetizelab",
        "name": "MonetizeLab",
        "url": "https://monetizelab.online",
        "target": "Marketing Agency, Web Agency & Content Creator",
        "core_pitch": (
            "Piattaforma per agenzie marketing e content creator per scalare acquisizione clienti, "
            "produzione contenuti e monetizzazione ricorrente."
        ),
        "cta": "Scopri i piani dedicati ad agenzie e creator su https://monetizelab.online",
    },
    "tecnicolive": {
        "key": "tecnicolive",
        "name": "TecnicoLIVE",
        "url": "https://www.tecnicolive.it",
        "target": "Termoidraulici, Elettricisti, Caldaisti & Installatori Impianti",
        "core_pitch": (
            "Assistente vocale AI H24 con chiamate simultanee illimitate (Base 169€/m, Pro 269€/m, "
            "Business 369€/m, -20% annuale) + associazione CNA Catania al 50% per il 1° anno."
        ),
        "cta": "Testa il centralino vocale AI al +39 095 342 0411 o su https://www.tecnicolive.it",
    },
    "rsksystem": {
        "key": "rsksystem",
        "name": "RSK System",
        "url": "https://rsksystem.com",
        "target": "PMI Italiane & Europee B2B/B2C",
        "core_pitch": (
            "CRM sovrano, Smart Lists dinamiche, automazioni multicanale WhatsApp/Email e sincronizzazione "
            "Meta Ads per nutrire i lead e aumentare le conversioni."
        ),
        "cta": "Attiva la pipeline CRM & automazioni su https://rsksystem.com",
    },
}

_TECNICOLIVE_ATECO_PREFIXES = ("43.21", "43.22", "43.29", "33.12", "33.20")
_MONETIZELAB_ATECO_PREFIXES = ("73.11", "73.12", "74.10", "59.11", "59.12", "62.01", "63.11", "70.21")

_TECNICOLIVE_KEYWORDS_RE = re.compile(
    r"\b("
    r"termoidraulic\w*|idraulic\w*|caldais\w*|caldai\w*|climatizz\w*|condizionat\w*|hvac|"
    r"elettricist\w*|impianti\s+elettrici|pompe\s+di\s+calore|frigorist\w*|bruciator\w*|"
    r"scaldabagn\w*|plumber|electrician|heating\s+contractor|air\s+conditioning|fotovoltaico|"
    r"impiantistic\w*"
    r")\b",
    re.IGNORECASE,
)

_MONETIZELAB_KEYWORDS_RE = re.compile(
    r"\b("
    r"marketing\s+agency|agenzia\s+(?:di\s+)?(?:marketing|comunicazione|pubblicit\w*|creativ\w*)|"
    r"web\s+agency|digital\s+(?:agency|marketing)|social\s+media\s+(?:agency|manager)|"
    r"content\s+creator|creator\b|influencer|video\s+production|agenzia\s+seo|performance\s+marketing|"
    r"media\s+agency|advertising|branding\s+studio"
    r")\b",
    re.IGNORECASE,
)


def route_lead_to_product(
    company_name: str,
    category: str = "",
    niche: str = "",
    ateco_code: str = "",
    website_text: str = "",
    override_product: Optional[UpsellProduct] = None,
) -> Dict[str, Any]:
    """
    Smista automaticamente il lead sul prodotto ideale dell'ecosistema:
    1. monetizelab.online -> Agenzie marketing, web agency, content creator
    2. tecnicolive.it -> Termoidraulici, elettricisti, impiantisti
    3. rsksystem.com -> Tutte le altre PMI italiane/europee
    """
    if override_product and override_product in PRODUCT_CATALOG:
        prod = PRODUCT_CATALOG[override_product]
        return {
            "product_key": prod["key"],
            "product_name": prod["name"],
            "product_url": prod["url"],
            "rationale": f"Routing esplicito da configurazione campagna su {prod['name']}.",
            "core_pitch": prod["core_pitch"],
            "cta": prod["cta"],
        }

    ateco_clean = (ateco_code or "").strip()
    if ateco_clean:
        if ateco_clean.startswith(_TECNICOLIVE_ATECO_PREFIXES):
            prod = PRODUCT_CATALOG["tecnicolive"]
            return {
                "product_key": prod["key"],
                "product_name": prod["name"],
                "product_url": prod["url"],
                "rationale": f"Codice ATECO impiantistico ({ateco_clean}) -> TecnicoLIVE.",
                "core_pitch": prod["core_pitch"],
                "cta": prod["cta"],
            }
        if ateco_clean.startswith(_MONETIZELAB_ATECO_PREFIXES):
            prod = PRODUCT_CATALOG["monetizelab"]
            return {
                "product_key": prod["key"],
                "product_name": prod["name"],
                "product_url": prod["url"],
                "rationale": f"Codice ATECO agenzia/media/digital ({ateco_clean}) -> MonetizeLab.",
                "core_pitch": prod["core_pitch"],
                "cta": prod["cta"],
            }

    combined = f"{company_name} {category} {niche} {website_text}".strip()
    if _TECNICOLIVE_KEYWORDS_RE.search(combined):
        prod = PRODUCT_CATALOG["tecnicolive"]
        return {
            "product_key": prod["key"],
            "product_name": prod["name"],
            "product_url": prod["url"],
            "rationale": "Settore impiantistica/termoidraulica/elettrico rilevato -> TecnicoLIVE.",
            "core_pitch": prod["core_pitch"],
            "cta": prod["cta"],
        }

    if _MONETIZELAB_KEYWORDS_RE.search(combined):
        prod = PRODUCT_CATALOG["monetizelab"]
        return {
            "product_key": prod["key"],
            "product_name": prod["name"],
            "product_url": prod["url"],
            "rationale": "Settore Marketing Agency / Content Creator rilevato -> MonetizeLab.",
            "core_pitch": prod["core_pitch"],
            "cta": prod["cta"],
        }

    prod = PRODUCT_CATALOG["rsksystem"]
    return {
        "product_key": prod["key"],
        "product_name": prod["name"],
        "product_url": prod["url"],
        "rationale": "PMI generica B2B/B2C -> RSK System (CRM, automazioni WhatsApp/Email e nurturing).",
        "core_pitch": prod["core_pitch"],
        "cta": prod["cta"],
    }
