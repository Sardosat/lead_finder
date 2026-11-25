import asyncio

from fastapi.testclient import TestClient

from api.auth import create_session_token, SESSION_COOKIE_NAME
from api.server import app
from engine.intelligence.market_radar import MarketRadarService


def test_compute_dataset_pain_points_returns_real_counts():
    leads = [
        {"company_name": "Alfa Clima", "niche": "HVAC", "is_h24": False, "website": "", "cna_eligible_50": True, "email": "", "trigger_signal": "Picco Estivo"},
        {"company_name": "Beta Caldaie", "niche": "Termoidraulica", "is_h24": True, "website": "https://beta.it", "cna_eligible_50": False, "email": "info@beta.it", "trigger_signal": "Picco Estivo"},
    ]
    pains = MarketRadarService.compute_dataset_pain_points(leads, niche_filter="all")
    assert len(pains) >= 4
    missed = next(p for p in pains if p["id"] == "pain-missed-calls")
    assert missed["affected_count"] == 1
    assert missed["affected_pct"] == 50.0


def test_deterministic_social_posts_and_single_platform_regen():
    svc = MarketRadarService()
    svc.gemini_api_key = ""  # force deterministic path
    res = asyncio.run(
        svc.generate_social_posts(
            topic="Nuovo bando Conto Termico Sicilia",
            niche="termoidraulica",
            geography="sicilia",
            target_platform="linkedin",
            instruction="più breve",
        )
    )
    assert "facebook" in res and "instagram" in res and "linkedin" in res
    for key in ("facebook", "instagram", "linkedin"):
        assert len(res[key]["text"]) > 20
        assert len(res[key]["image_prompt"]) > 20
    assert len(res["hashtags"]) >= 5
    assert res["regenerated_platform"] == "linkedin"


def test_radar_api_endpoints_authenticated():
    client = TestClient(app)
    token, _ = create_session_token("admin")
    client.cookies.set(SESSION_COOKIE_NAME, token)

    r1 = client.post("/radar/trends", json={"search_id": "ds-master-clean", "niche": "termoidraulica", "geography": "sicilia", "timeframe": "30d"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert "pain_points" in d1 and "hashtags" in d1

    r2 = client.post("/radar/facebook-leads", json={"search_id": "ds-master-clean", "niche": "all", "limit": 5})
    assert r2.status_code == 200
    d2 = r2.json()
    assert "items" in d2

    r3 = client.post("/radar/social-posts", json={"topic": "Bando PNRR Impianti Sicilia", "niche": "termoidraulica", "geography": "sicilia"})
    assert r3.status_code == 200
    d3 = r3.json()
    assert "facebook" in d3 and "instagram" in d3 and "linkedin" in d3
