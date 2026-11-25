from pathlib import Path
import time

import pytest
from fastapi.testclient import TestClient

from api.server import app


@pytest.fixture()
def isolated_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("LEAD_ENGINE_DB_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("LEAD_ENGINE_EXPORTS_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("LEAD_ENGINE_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("LEAD_ENGINE_SUPPRESSION_PATH", str(tmp_path / "suppression.csv"))
    monkeypatch.setenv("AUTH_USERNAME", "tester")
    monkeypatch.setenv("AUTH_PASSWORD", "supersecret99")
    monkeypatch.setenv("AUTH_SECRET", "unit-test-hmac-secret")

    client = TestClient(app)
    r_bad = client.post("/auth/login", json={"username": "tester", "password": "wrong"})
    assert r_bad.status_code == 401

    r_ok = client.post("/auth/login", json={"username": "tester", "password": "supersecret99"})
    assert r_ok.status_code == 200
    data = r_ok.json()
    assert data["authenticated"] is True
    assert data["using_default_password"] is False
    return client


def test_auth_me_and_logout(isolated_client: TestClient):
    r_me = isolated_client.get("/auth/me")
    assert r_me.status_code == 200
    assert r_me.json()["username"] == "tester"

    r_out = isolated_client.post("/auth/logout")
    assert r_out.status_code == 200
    assert isolated_client.get("/auth/me").status_code == 401


def test_analytics_overview_trends_and_clay_benchmark(isolated_client: TestClient):
    ov = isolated_client.get("/analytics/overview?search_id=ds-master-clean")
    assert ov.status_code == 200
    body = ov.json()
    assert body["kpis"]["total_leads"] > 0
    assert len(body["quality_funnel"]) == 5
    assert len(body["product_tier_matrix"]) == 3
    assert len(body["geo_coverage"]) > 0

    bench = isolated_client.get("/analytics/clay-benchmark")
    assert bench.status_code == 200
    bjson = bench.json()
    assert bjson["clay_summary"]["total_rows"] == 50
    assert bjson["clay_summary"]["non_italy_count"] >= 3
    assert bjson["engine_summary"]["italy_accuracy_pct"] == 100.0

    tr = isolated_client.get("/analytics/trends?search_id=ds-master-clean")
    assert tr.status_code == 200
    tjson = tr.json()
    assert "STIMA TEORICA" in tjson["disclaimer"]
    assert len(tjson["seasonality_12m"]) == 12
    assert tjson["real_intent_signals"]["total_analyzed"] > 0


def test_searches_crud_and_background_run(isolated_client: TestClient):
    r_list = isolated_client.get("/searches")
    assert r_list.status_code == 200
    ids = {s["id"] for s in r_list.json()["searches"]}
    assert "ds-outbound-tecnicolive" in ids
    assert "ds-master-clean" in ids

    # Impossibile eliminare archivi built-in
    r_del_builtin = isolated_client.delete("/searches/ds-master-clean")
    assert r_del_builtin.status_code == 400

    # Creazione ricerca custom + run locale verificato
    r_create = isolated_client.post(
        "/searches",
        json={
            "name": "Test Impiantisti Acireale",
            "target_vertical": "Termoidraulica Climatizzazione",
            "ateco_codes": ["43.22.01"],
            "search_queries": ["termoidraulica Acireale"],
            "geo": {"country_code": "IT", "province_code": "CT", "municipalities": ["Acireale"], "strict_country_lock": True},
            "product_target": "tecnicolive",
            "offer_summary": "TecnicoLIVE + CNA 50%",
            "enrichment": {
                "enable_l1_tech_audit": False,
                "enable_l1_mx_check": False,
                "enable_l1_vies": False,
                "enable_l2_gemini_ai": False,
                "enable_l3_openapi_registry": False,
                "max_l3_budget_eur": 0.0,
            },
            "run_now": False,
        },
    )
    assert r_create.status_code == 200
    sid = r_create.json()["id"]

    r_run = isolated_client.post(f"/searches/{sid}/run")
    assert r_run.status_code == 200

    # Attende brevemente completamento background task TestClient
    for _ in range(15):
        st = isolated_client.get(f"/searches/{sid}").json()
        if st["status"] in ("ready", "failed"):
            break
        time.sleep(0.1)

    r_dup = isolated_client.post(f"/searches/{sid}/duplicate")
    assert r_dup.status_code == 200
    dup_id = r_dup.json()["id"]

    assert isolated_client.delete(f"/searches/{sid}").status_code == 200
    assert isolated_client.delete(f"/searches/{dup_id}").status_code == 200


def test_lead_explorer_and_exports_hitl_and_suppression(isolated_client: TestClient):
    r_leads = isolated_client.get("/leads?search_id=ds-outbound-tecnicolive&view=callable_ab&page_size=10")
    assert r_leads.status_code == 200
    ldata = r_leads.json()
    assert ldata["total"] > 0
    assert len(ldata["items"]) <= 10
    first = ldata["items"][0]
    assert first["phone_e164"].startswith("+39")
    assert "pec" not in first["email"].lower()

    r_facets = isolated_client.get("/leads/facets?search_id=ds-outbound-tecnicolive")
    assert r_facets.status_code == 200
    assert len(r_facets.json()["cities"]) > 0

    # Aggiunta a blacklist e verifica blocco
    r_sup_add = isolated_client.post(
        "/compliance/suppression",
        json={"phone_e164": first["phone_e164"], "reason": "CANCELLAMI TEST"},
    )
    assert r_sup_add.status_code == 200
    assert len(r_sup_add.json()["entries"]) >= 1

    # Generazione export CSV & WEBHOOK_JSON -> esclude automaticamente lead in blacklist
    r_exp_csv = isolated_client.post(
        "/exports/generate",
        json={
            "search_id": "ds-outbound-tecnicolive",
            "format": "CSV",
            "lead_ids": [first["id"], ldata["items"][1]["id"]],
            "filename_prefix": "test_csv",
        },
    )
    assert r_exp_csv.status_code == 200
    exp_csv = r_exp_csv.json()
    assert exp_csv["row_count"] == 1
    assert exp_csv["blocked_count"] >= 1

    r_prev = isolated_client.get(f"/exports/{exp_csv['id']}/preview")
    assert r_prev.status_code == 200
    assert len(r_prev.json()["rows"]) == 1

    r_dl = isolated_client.get(f"/exports/{exp_csv['id']}/download")
    assert r_dl.status_code == 200
    assert len(r_dl.content) > 20

    # Export XLSX + Webhook HITL check
    r_exp_wh = isolated_client.post(
        "/exports/generate",
        json={
            "search_id": "ds-outbound-tecnicolive",
            "format": "WEBHOOK_JSON",
            "lead_ids": [ldata["items"][1]["id"]],
            "filename_prefix": "test_wh",
        },
    )
    assert r_exp_wh.status_code == 200
    wh_id = r_exp_wh.json()["id"]
    assert isolated_client.post(f"/exports/{wh_id}/approve", json={"human_approved": False}).status_code == 400
    r_appr = isolated_client.post(f"/exports/{wh_id}/approve", json={"human_approved": True, "dispatch_webhook": False})
    assert r_appr.status_code == 200
    assert r_appr.json()["record"]["approval_status"] == "APPROVED"

    assert isolated_client.delete(f"/exports/{exp_csv['id']}").status_code == 200
    assert isolated_client.delete(f"/exports/{wh_id}").status_code == 200

    # Rimozione opt-out
    r_sup_del = isolated_client.delete(f"/compliance/suppression?phone_e164={first['phone_e164'].replace('+', '%2B')}")
    assert r_sup_del.status_code == 200


def test_outreach_and_settings_never_leak_secrets(isolated_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENAPI_API_KEY", "SECRET_API_KEY_NEVER_LEAK_12345")
    r_out = isolated_client.get("/outreach/drafts?search_id=ds-outbound-tecnicolive&page_size=5")
    assert r_out.status_code == 200
    odata = r_out.json()
    assert len(odata["drafts"]) > 0
    assert odata["pricing_plans"]["base"]["monthly"] == 169
    assert odata["pricing_plans"]["pro"]["monthly"] == 269
    assert odata["pricing_plans"]["business"]["monthly"] == 369
    assert odata["cna_first_year_discount_pct"] == 50

    r_set = isolated_client.get("/settings/status")
    assert r_set.status_code == 200
    assert "SECRET_API_KEY_NEVER_LEAK_12345" not in r_set.text
