"""
openapi_italy.py — Connettore Livello 3 per dati camerali italiani ufficiali Openapi.com
(`company.openapi.com` e `test.company.openapi.com`).

Sicurezza:
- Carica credenziali esclusivamente da .env (OPENAPI_API_KEY, OPENAPI_USERNAME, OPENAPI_TOKEN, OPENAPI_ENV).
- Non logga mai chiavi API o token Bearer.
- Implementa cache su disco (data/openapi_cache.json) e tetto massimo di spesa (max_budget_eur).
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp
from dotenv import load_dotenv

from src.config import DATA_DIR, ROOT_DIR
from src.piva_validator import clean_piva

logger = logging.getLogger("openapi_italy")

OPENAPI_CACHE_FILE = DATA_DIR / "openapi_cache.json"

ENDPOINT_COST_ESTIMATE_EUR = {
    "IT-start": 0.05,
    "IT-advanced": 0.35,
    "IT-pec": 0.05,
    "IT-search": 0.10,
}


class OpenapiItalyClient:
    """Client asincrono per Openapi.com Italian Company API con gestione OAuth2, cache e budget."""

    def __init__(
        self,
        cache_path: Path = OPENAPI_CACHE_FILE,
        max_budget_eur: float = 5.0,
        env_override: Optional[str] = None,
    ):
        load_dotenv(ROOT_DIR / ".env", override=False)
        self.env = (env_override or os.getenv("OPENAPI_ENV", "production")).strip().lower()
        self.api_key = os.getenv("OPENAPI_API_KEY", "").strip()
        self.username = os.getenv("OPENAPI_USERNAME", "").strip()
        self.token = os.getenv("OPENAPI_TOKEN", "").strip()
        self.max_budget_eur = float(max_budget_eur)
        self.session_spent_eur = 0.0
        self.cache_path = cache_path
        self._cache: Dict[str, Dict[str, Any]] = self._load_cache()

        if self.env == "sandbox":
            self.company_host = "test.company.openapi.com"
            self.oauth_host = "test.oauth.openapi.com"
        else:
            self.company_host = "company.openapi.com"
            self.oauth_host = "oauth.openapi.com"

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

    def has_credentials(self) -> bool:
        return bool(self.token or (self.api_key and self.username))

    async def _ensure_bearer_token(self, session: aiohttp.ClientSession, endpoint: str) -> Dict[str, Any]:
        """Restituisce un Bearer token valido o un errore strutturato (senza esporre segreti)."""
        if self.token:
            return {"status": "OK", "token": self.token}
        if not (self.api_key and self.username):
            return {
                "status": "NO_CREDENTIALS",
                "message": (
                    "Credenziali Openapi mancanti in .env: imposta OPENAPI_TOKEN oppure "
                    "OPENAPI_USERNAME + OPENAPI_API_KEY."
                ),
            }

        token_url = f"https://{self.oauth_host}/token"
        scopes = [
            f"GET:{self.company_host}/IT-start",
            f"GET:{self.company_host}/IT-advanced",
            f"GET:{self.company_host}/IT-pec",
            f"GET:{self.company_host}/IT-search",
        ]
        try:
            basic_header = aiohttp.helpers.BasicAuth(self.username, self.api_key).encode()
            if hasattr(aiohttp, "encode_basic_auth"):
                basic_header = aiohttp.encode_basic_auth(self.username, self.api_key)
            async with session.post(
                token_url,
                json={"scopes": scopes, "ttl": 3600},
                headers={
                    "Authorization": basic_header,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=12),
            ) as resp:
                raw_txt = await resp.text()
                try:
                    body = json.loads(raw_txt) if raw_txt.strip() else {}
                except Exception:
                    body = {"raw_error": raw_txt[:200]}

                if resp.status in (200, 201) and isinstance(body, dict) and body.get("token"):
                    self.token = str(body["token"])
                    return {"status": "OK", "token": self.token}
                err_msg = (
                    body.get("message")
                    or body.get("error")
                    or f"HTTP {resp.status}"
                )
                return {
                    "status": "AUTH_ERROR",
                    "http_status": resp.status,
                    "message": (
                        f"Autenticazione Openapi ({err_msg}): crea un Production Token in "
                        "console.openapi.com/oauth (+ New token -> imposta OPENAPI_TOKEN in .env) "
                        "oppure attiva il Sandbox e imposta OPENAPI_ENV=sandbox."
                    ),
                }
        except Exception as e:
            return {"status": "NETWORK_ERROR", "message": f"Errore OAuth2 Openapi: {e}"}

    @staticmethod
    def parse_company_payload(endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Estrae i campi italiani/europei normalizzati da IT-start / IT-advanced / IT-pec."""
        data = payload.get("data") or {}
        if isinstance(data, list):
            data = data[0] if data else {}

        reg_office = ((data.get("address") or {}).get("registeredOffice") or {})
        region_obj = reg_office.get("region") or {}
        ateco_obj = data.get("atecoClassification") or {}
        if isinstance(ateco_obj, list):
            ateco_obj = ateco_obj[0] if ateco_obj else {}

        # Estrazione ricavi / dipendenti se presenti in IT-advanced
        revenue_eur = None
        employees = None
        balance_sheets = data.get("balanceSheets") or {}
        last_bs = balance_sheets.get("last") if isinstance(balance_sheets, dict) else None
        if isinstance(last_bs, dict):
            revenue_eur = last_bs.get("turnover") or last_bs.get("revenues")
            employees = last_bs.get("employees")

        ateco_code = str(
            ateco_obj.get("atecoCode")
            or data.get("atecoCode")
            or data.get("ateco")
            or ""
        ).strip()
        ateco_desc = str(
            ateco_obj.get("atecoDescription")
            or ateco_obj.get("description")
            or ""
        ).strip()

        return {
            "status": "OK",
            "endpoint": endpoint,
            "company_name": str(data.get("companyName") or "").strip(),
            "vat_id": f"IT{data['vatCode']}" if data.get("vatCode") else "",
            "tax_code": str(data.get("taxCode") or "").strip(),
            "activity_status": str(data.get("activityStatus") or "").strip(),
            "sdi_code": str(data.get("sdiCode") or "").strip(),
            "forma_giuridica": str(data.get("legalForm") or data.get("companyType") or "").strip(),
            "rea_code": str(data.get("reaCode") or data.get("rea") or "").strip(),
            "cciaa": str(data.get("cciaa") or reg_office.get("province") or "").strip(),
            "ateco_code": ateco_code,
            "ateco_description": ateco_desc,
            "pec": str(data.get("pec") or "").strip().lower(),
            "city": str(reg_office.get("town") or "").strip().title(),
            "province": str(reg_office.get("province") or "").strip().upper(),
            "postal_code": str(reg_office.get("zipCode") or "").strip(),
            "cadastral_code": str(reg_office.get("townCode") or "").strip().upper(),
            "region": str(region_obj.get("description") or "").strip().title(),
            "address": str(reg_office.get("streetName") or "").strip(),
            "revenue_eur": float(revenue_eur) if revenue_eur is not None else None,
            "employees_count": int(employees) if employees is not None else None,
        }

    async def query_company(
        self,
        vat_or_cf: str,
        endpoint: str = "IT-start",
        session: Optional[aiohttp.ClientSession] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Interroga /IT-start, /IT-advanced o /IT-pec con cache e guardia budget."""
        cleaned = clean_piva(vat_or_cf) or (vat_or_cf or "").strip().upper()
        if not cleaned:
            return {"status": "INVALID_INPUT", "message": "Partita IVA o Codice Fiscale mancante"}

        cache_key = f"{self.env}:{endpoint}:{cleaned}"
        if use_cache and cache_key in self._cache:
            res = dict(self._cache[cache_key])
            res["cached"] = True
            return res

        est_cost = ENDPOINT_COST_ESTIMATE_EUR.get(endpoint, 0.10)
        if self.session_spent_eur + est_cost > self.max_budget_eur:
            return {
                "status": "BUDGET_EXCEEDED",
                "message": f"Tetto sessione ({self.max_budget_eur:.2f}€) raggiunto: richiesta {endpoint} bloccata.",
            }

        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()

        try:
            auth_res = await self._ensure_bearer_token(session, endpoint)
            if auth_res.get("status") != "OK":
                return auth_res

            url = f"https://{self.company_host}/{endpoint}/{cleaned}"
            headers = {
                "Authorization": f"Bearer {auth_res['token']}",
                "Accept": "application/json",
            }
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                body = await resp.json(content_type=None)
                if resp.status == 200 and isinstance(body, dict) and body.get("success", True):
                    parsed = self.parse_company_payload(endpoint, body)
                    parsed["cached"] = False
                    parsed["estimated_cost_eur"] = est_cost
                    self.session_spent_eur += est_cost
                    self._cache[cache_key] = parsed
                    self._save_cache()
                    return parsed
                if resp.status == 402:
                    return {
                        "status": "INSUFFICIENT_CREDITS",
                        "http_status": 402,
                        "message": "Credito Openapi insufficiente (effettuare ricarica o attivare Sandbox).",
                    }
                if resp.status in (401, 403):
                    return {
                        "status": "AUTH_ERROR",
                        "http_status": resp.status,
                        "message": "Token non autorizzato per questo endpoint/scope Openapi.",
                    }
                if resp.status == 404:
                    return {
                        "status": "NOT_FOUND",
                        "http_status": 404,
                        "message": f"Nessuna impresa trovata su {endpoint} per {cleaned}.",
                    }
                return {
                    "status": f"HTTP_{resp.status}",
                    "http_status": resp.status,
                    "message": str((body or {}).get("message") or f"Errore Openapi HTTP {resp.status}"),
                }
        except Exception as e:
            logger.debug(f"Errore chiamata Openapi {endpoint}: {e}")
            return {"status": "NETWORK_ERROR", "message": str(e)}
        finally:
            if own_session:
                await session.close()
