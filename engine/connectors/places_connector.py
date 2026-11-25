"""
places_connector.py — Connettore Seed Discovery (Opzione A: Serper Places & Google Places API New)
con Geo-Lock rigoroso ISTAT/Provincia/Paese per eliminare gli errori di Clay.com (es. Valverde -> Ecuador/Spagna).
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

import aiohttp
from dotenv import load_dotenv

from engine.schemas.campaign import CampaignConfig, GeoFilter
from engine.schemas.lead import LeadRecord
from src.config import ROOT_DIR
from src.normalizers import (
    clean_company_website,
    is_anti_persona_retail,
    is_mobile_e164,
    normalize_city_and_area,
    normalize_phone_e164,
)

logger = logging.getLogger("places_connector")

_FOREIGN_COUNTRIES_IN_ADDRESS = (
    "ecuador",
    "spain",
    "españa",
    "spagna",
    "malta",
    "france",
    "germany",
    "united kingdom",
    "usa",
    "united states",
    "pichincha",
    "segovia",
    "valverde del majano",
)


def is_within_geo_filter(address: str, country: str, geo: GeoFilter) -> bool:
    """
    Geo-Lock rigoroso: blocca omonimi esteri (es. Valverde -> Ecuador/Spagna, Malta)
    che Clay.com include erroneamente nei risultati di ricerca per area.
    """
    addr_lower = (address or "").lower()
    country_upper = (country or "").strip().upper()
    target_cc = geo.country_code.strip().upper()

    if geo.strict_country_lock:
        if country_upper and country_upper not in (target_cc, "ITALY" if target_cc == "IT" else target_cc):
            return False
        if target_cc == "IT" and any(bad in addr_lower for bad in _FOREIGN_COUNTRIES_IN_ADDRESS):
            return False

    if geo.province_code and target_cc == "IT":
        prov = geo.province_code.strip().upper()
        # Se l'indirizzo riporta una sigla provincia esplicita diversa (es. "(RM)" mentre cerco "(CT)")
        m = re.search(r"\(([A-Z]{2})\)", address or "")
        if m and m.group(1) != prov:
            return False

    if geo.municipalities and addr_lower:
        muni_match = any(m.lower() in addr_lower for m in geo.municipalities)
        if not muni_match and geo.province_code:
            # Accetta comunque se nella provincia target (es. CAP 95xxx per CT)
            if geo.province_code.upper() == "CT" and not re.search(r"\b95\d{3}\b", addr_lower):
                return False

    return True


class PlacesDiscoveryClient:
    """Seed Discovery tramite Serper.dev Places o Google Places API (New)."""

    def __init__(self):
        load_dotenv(ROOT_DIR / ".env", override=False)
        self.serper_api_key = os.getenv("SERPER_API_KEY", "").strip()
        self.google_places_key = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()

    @staticmethod
    def _extract_postal_and_city(address: str, geo: GeoFilter) -> tuple[str, str]:
        m_cap = re.search(r"\b(\d{5})\b", address or "")
        postal_code = m_cap.group(1) if m_cap else ""
        city_hint = ""
        for m in geo.municipalities:
            if m.lower() in (address or "").lower():
                city_hint = m
                break
        city, _ = normalize_city_and_area(city_hint, address)
        return postal_code, city

    def normalize_serper_item(self, item: Dict[str, Any], campaign: CampaignConfig) -> Optional[LeadRecord]:
        name = str(item.get("title") or "").strip()
        address = str(item.get("address") or "").strip()
        category = str(item.get("category") or "").strip()
        website = clean_company_website(str(item.get("website") or ""))
        if not name or is_anti_persona_retail(name, category, website):
            return None
        if not is_within_geo_filter(address, campaign.geo.country_code, campaign.geo):
            return None

        p1, p2 = normalize_phone_e164(item.get("phoneNumber") or item.get("phone") or "")
        postal_code, city = self._extract_postal_and_city(address, campaign.geo)
        rating = item.get("rating")
        reviews = item.get("ratingCount") or item.get("reviews")

        return LeadRecord(
            company_name=name,
            country_code=campaign.geo.country_code.upper(),
            region=campaign.geo.region,
            province=campaign.geo.province_code.upper(),
            city=city,
            postal_code=postal_code,
            address=address,
            phone_e164=p1,
            phone_secondary=p2,
            phone_type="Mobile" if is_mobile_e164(p1) else ("Fisso" if p1 else "Unknown"),
            website=website,
            source="serper_places",
            google_place_id=str(item.get("cid") or item.get("placeId") or ""),
            google_rating=float(rating) if rating is not None else None,
            google_reviews_count=int(reviews) if reviews is not None else None,
            category=category,
            niche=campaign.target_vertical,
        )

    def normalize_google_place_item(self, item: Dict[str, Any], campaign: CampaignConfig) -> Optional[LeadRecord]:
        display = item.get("displayName") or {}
        name = str(display.get("text") if isinstance(display, dict) else display or "").strip()
        address = str(item.get("formattedAddress") or "").strip()
        category = str(item.get("primaryTypeDisplayName", {}).get("text", "") if isinstance(item.get("primaryTypeDisplayName"), dict) else "")
        website = clean_company_website(str(item.get("websiteUri") or ""))

        if not name or is_anti_persona_retail(name, category, website):
            return None
        if not is_within_geo_filter(address, campaign.geo.country_code, campaign.geo):
            return None

        raw_phone = item.get("internationalPhoneNumber") or item.get("nationalPhoneNumber") or ""
        p1, p2 = normalize_phone_e164(raw_phone)
        postal_code, city = self._extract_postal_and_city(address, campaign.geo)
        rating = item.get("rating")
        reviews = item.get("userRatingCount")

        return LeadRecord(
            company_name=name,
            country_code=campaign.geo.country_code.upper(),
            region=campaign.geo.region,
            province=campaign.geo.province_code.upper(),
            city=city,
            postal_code=postal_code,
            address=address,
            phone_e164=p1,
            phone_secondary=p2,
            phone_type="Mobile" if is_mobile_e164(p1) else ("Fisso" if p1 else "Unknown"),
            website=website,
            source="google_places_new",
            google_place_id=str(item.get("id") or ""),
            google_rating=float(rating) if rating is not None else None,
            google_reviews_count=int(reviews) if reviews is not None else None,
            category=category,
            niche=campaign.target_vertical,
        )

    async def search_campaign_seeds(
        self,
        campaign: CampaignConfig,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> Dict[str, Any]:
        """Esegue le query geografiche su Serper Places o Google Places New."""
        if not (self.serper_api_key or self.google_places_key):
            return {
                "status": "NO_API_KEY",
                "message": "Imposta SERPER_API_KEY o GOOGLE_PLACES_API_KEY in .env per discovery live.",
                "leads": [],
            }

        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()

        leads: List[LeadRecord] = []
        seen_keys = set()

        try:
            for query in campaign.search_queries:
                if self.serper_api_key:
                    url = "https://google.serper.dev/places"
                    payload = {
                        "q": query,
                        "gl": campaign.geo.country_code.lower(),
                        "hl": "it" if campaign.geo.country_code.upper() == "IT" else "en",
                    }
                    async with session.post(
                        url,
                        json=payload,
                        headers={"X-API-KEY": self.serper_api_key, "Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            for item in (data.get("places") or [])[: campaign.max_results_per_query]:
                                rec = self.normalize_serper_item(item, campaign)
                                if rec:
                                    k = (rec.company_name.lower(), rec.city.lower())
                                    if k not in seen_keys:
                                        seen_keys.add(k)
                                        leads.append(rec)
                elif self.google_places_key:
                    url = "https://places.googleapis.com/v1/places:searchText"
                    headers = {
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": self.google_places_key,
                        "X-Goog-FieldMask": (
                            "places.id,places.displayName,places.formattedAddress,"
                            "places.internationalPhoneNumber,places.nationalPhoneNumber,"
                            "places.websiteUri,places.rating,places.userRatingCount,places.primaryTypeDisplayName"
                        ),
                    }
                    body = {
                        "textQuery": query,
                        "languageCode": "it" if campaign.geo.country_code.upper() == "IT" else "en",
                        "regionCode": campaign.geo.country_code.upper(),
                        "maxResultCount": min(20, campaign.max_results_per_query),
                    }
                    async with session.post(
                        url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            for item in data.get("places") or []:
                                rec = self.normalize_google_place_item(item, campaign)
                                if rec:
                                    k = (rec.company_name.lower(), rec.city.lower())
                                    if k not in seen_keys:
                                        seen_keys.add(k)
                                        leads.append(rec)
        except Exception as e:
            logger.warning(f"Errore Places Discovery: {e}")
            return {"status": "ERROR", "message": str(e), "leads": leads}
        finally:
            if own_session:
                await session.close()

        return {"status": "OK", "leads": leads, "count": len(leads)}
