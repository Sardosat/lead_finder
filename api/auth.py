"""
auth.py — Autenticazione sessione stateless HMAC-SHA256 per Lead Intelligence Engine API.

Supporta:
- Cookie HttpOnly ('lf_session') impostato al login e inviato automaticamente dal browser/proxy Next.js
- Header 'Authorization: Bearer <token>' o 'X-API-Key: <token>' per chiamate programmatiche
"""

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv
from fastapi import HTTPException, Request, status

from src.config import ROOT_DIR

load_dotenv(ROOT_DIR / ".env", override=False)

SESSION_COOKIE_NAME = "lf_session"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 giorni
_DEFAULT_USERNAME = "admin"
_DEFAULT_PASSWORD = "tecnicolive2026"


def get_auth_username() -> str:
    return (os.getenv("AUTH_USERNAME") or _DEFAULT_USERNAME).strip() or _DEFAULT_USERNAME


def get_auth_password() -> str:
    return (os.getenv("AUTH_PASSWORD") or _DEFAULT_PASSWORD).strip() or _DEFAULT_PASSWORD


def is_using_default_password() -> bool:
    env_pwd = (os.getenv("AUTH_PASSWORD") or "").strip()
    return not env_pwd or env_pwd == _DEFAULT_PASSWORD


def _get_signing_secret() -> bytes:
    raw = (os.getenv("AUTH_SECRET") or "").strip()
    if raw:
        return raw.encode("utf-8")
    derived = hashlib.sha256(f"lead-engine-it-eu:{get_auth_password()}".encode("utf-8")).hexdigest()
    return derived.encode("utf-8")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def verify_credentials(username: str, password: str) -> bool:
    expected_user = get_auth_username()
    expected_pwd = get_auth_password()
    user_ok = hmac.compare_digest((username or "").strip().encode("utf-8"), expected_user.encode("utf-8"))
    pwd_ok = hmac.compare_digest((password or "").encode("utf-8"), expected_pwd.encode("utf-8"))
    return user_ok and pwd_ok


def create_session_token(username: str, ttl_seconds: int = SESSION_TTL_SECONDS) -> Tuple[str, int]:
    expires_at = int(time.time()) + ttl_seconds
    payload = json.dumps({"sub": username, "exp": expires_at}, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload)
    sig = hmac.new(_get_signing_secret(), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}", expires_at


def verify_session_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig = token.strip().split(".", 1)
        expected_sig = hmac.new(_get_signing_secret(), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp", 0)) <= int(time.time()):
            return None
        if not payload.get("sub"):
            return None
        return payload
    except Exception:
        return None


def extract_token_from_request(request: Request) -> Optional[str]:
    cookie_tok = request.cookies.get(SESSION_COOKIE_NAME)
    if cookie_tok:
        return cookie_tok
    auth_header = request.headers.get("Authorization") or ""
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key.strip()
    return None


def require_auth(request: Request) -> Dict[str, Any]:
    token = extract_token_from_request(request)
    payload = verify_session_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticazione richiesta per accedere al Lead Intelligence Engine.",
        )
    return payload
