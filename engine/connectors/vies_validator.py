"""
vies_validator.py — Client asincrono per l'API REST ufficiale gratuita VIES della Commissione Europea.
Verifica in tempo reale se una Partita IVA IT/UE è valida e attiva per operazioni intra-UE.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp

from src.config import DATA_DIR
from src.piva_validator import clean_piva, validate_piva

logger = logging.getLogger("vies_validator")

VIES_CACHE_FILE = DATA_DIR / "vies_cache.json"
VIES_ENDPOINT_TEMPLATE = "https://ec.europa.eu/taxation_customs/vies/rest-api/ms/{country_code}/vat/{vat_number}"


def parse_vat_identifier(vat_id: str, default_country: str = "IT") -> tuple[str, str]:
    """Divide 'IT06200390877' in ('IT', '06200390877')."""
    raw = re.sub(r"[\s\.\-_]+", "", (vat_id or "").strip().upper())
    if not raw:
        return default_country.upper(), ""
    m = re.match(r"^([A-Z]{2})([A-Z0-9]+)$", raw)
    if m:
        return m.group(1), m.group(2)
    return default_country.upper(), raw


class ViesValidatorClient:
    """Validatore VIES UE con cache su disco e pre-controllo Luhn per l'Italia."""

    def __init__(self, cache_path: Path = VIES_CACHE_FILE):
        self.cache_path = cache_path
        self._cache: Dict[str, Dict[str, Any]] = self._load_cache()

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @staticmethod
    def parse_vies_payload(country_code: str, vat_number: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizza la risposta JSON dell'endpoint REST VIES."""
        is_valid = bool(payload.get("isValid") if "isValid" in payload else payload.get("valid", False))
        name = str(payload.get("name") or "").strip()
        address = str(payload.get("address") or "").strip()
        if name == "---":
            name = ""
        if address == "---":
            address = ""
        return {
            "status": "OK",
            "country_code": country_code,
            "vat_number": vat_number,
            "vat_id": f"{country_code}{vat_number}",
            "is_valid": is_valid,
            "user_error": str(payload.get("userError") or ""),
            "name": name,
            "address": address,
            "request_identifier": str(payload.get("requestIdentifier") or ""),
            "request_date": str(payload.get("requestDate") or ""),
        }

    async def check_vat(
        self,
        vat_id: str,
        default_country: str = "IT",
        session: Optional[aiohttp.ClientSession] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        country_code, vat_number = parse_vat_identifier(vat_id, default_country=default_country)
        if not vat_number:
            return {
                "status": "INVALID_INPUT",
                "vat_id": "",
                "is_valid": False,
                "error": "Partita IVA mancante o malformata",
            }

        if country_code == "IT":
            digits = clean_piva(vat_number)
            if not digits or not validate_piva(digits):
                return {
                    "status": "INVALID_LUHN",
                    "country_code": country_code,
                    "vat_number": vat_number,
                    "vat_id": f"{country_code}{vat_number}",
                    "is_valid": False,
                    "error": "Checksum Luhn italiano non valido",
                }
            vat_number = digits

        cache_key = f"{country_code}{vat_number}"
        if use_cache and cache_key in self._cache:
            cached = dict(self._cache[cache_key])
            cached["cached"] = True
            return cached

        url = VIES_ENDPOINT_TEMPLATE.format(country_code=country_code, vat_number=vat_number)
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()

        try:
            async with session.get(
                url,
                headers={"Accept": "application/json", "User-Agent": "LeadEngine-EU-VIES/1.0"},
                timeout=aiohttp.ClientTimeout(total=12),
            ) as resp:
                if resp.status != 200:
                    return {
                        "status": f"HTTP_{resp.status}",
                        "country_code": country_code,
                        "vat_number": vat_number,
                        "vat_id": cache_key,
                        "is_valid": None,
                        "error": f"VIES HTTP {resp.status}",
                    }
                payload = await resp.json(content_type=None)
                if payload.get("actionSucceed") is False or payload.get("errorWrappers"):
                    err_msgs = [
                        w.get("error", "") for w in (payload.get("errorWrappers") or []) if isinstance(w, dict)
                    ]
                    return {
                        "status": "VIES_SERVICE_UNAVAILABLE",
                        "country_code": country_code,
                        "vat_number": vat_number,
                        "vat_id": cache_key,
                        "is_valid": None,
                        "error": ", ".join(err_msgs) or "VIES temporaneamente non disponibile",
                    }

                result = self.parse_vies_payload(country_code, vat_number, payload)
                result["cached"] = False
                self._cache[cache_key] = result
                self._save_cache()
                return result
        except Exception as e:
            logger.debug(f"Errore VIES per {cache_key}: {e}")
            return {
                "status": "NETWORK_ERROR",
                "country_code": country_code,
                "vat_number": vat_number,
                "vat_id": cache_key,
                "is_valid": None,
                "error": str(e),
            }
        finally:
            if own_session:
                await session.close()
