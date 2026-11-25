from fastapi.testclient import TestClient

from api.auth import get_auth_password, get_auth_username
from api.server import app


def _authed_client() -> TestClient:
    client = TestClient(app)
    res = client.post(
        "/auth/login",
        json={"username": get_auth_username(), "password": get_auth_password()},
    )
    assert res.status_code == 200
    assert res.json()["authenticated"] is True
    return client


def test_unauthenticated_endpoints_require_login():
    anon = TestClient(app)
    assert anon.get("/health").status_code == 200
    assert anon.get("/products").status_code == 401
    assert anon.get("/leads").status_code == 401
    assert anon.get("/exports").status_code == 401


def test_health_and_products():
    client = _authed_client()
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_prod = client.get("/products")
    assert r_prod.status_code == 200
    keys = {p["key"] for p in r_prod.json()["products"]}
    assert keys == {"monetizelab", "rsksystem", "tecnicolive"}


def test_presets_and_routing_and_lia_endpoints(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAD_ENGINE_SUPPRESSION_PATH", str(tmp_path / "sup.csv"))
    client = _authed_client()

    r_pre = client.get("/campaigns/presets")
    assert r_pre.status_code == 200
    assert len(r_pre.json()["presets"]) == 3

    r_route = client.post(
        "/routing/classify",
        json={"company_name": "Studio Creativo Etna", "ateco_code": "73.11.01"},
    )
    assert r_route.status_code == 200
    assert r_route.json()["product_key"] == "monetizelab"

    r_lia = client.post(
        "/compliance/lia",
        json={
            "company_name": "Impianti Etna Srl",
            "vat_id": "IT06200390877",
            "city": "Catania",
            "phone": "347 1234567",
            "email": "etna@pec.it",
        },
    )
    assert r_lia.status_code == 200
    body = r_lia.json()
    assert body["assessment"]["status"] == "PASS"
    assert body["assessment"]["pec_cold_outreach_blocked"] is True
    assert body["sanitized_outbound_email"] == ""
    assert body["isolated_pec"] == "etna@pec.it"
    assert body["normalized_phone_e164"] == "+393471234567"
