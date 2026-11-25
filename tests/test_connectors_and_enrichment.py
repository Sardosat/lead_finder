import asyncio
from pathlib import Path

from engine.connectors.openapi_italy import OpenapiItalyClient
from engine.connectors.places_connector import PlacesDiscoveryClient, is_within_geo_filter
from engine.connectors.vies_validator import ViesValidatorClient, parse_vat_identifier
from engine.enrichment.gemini_qualifier import GeminiQualifier
from engine.enrichment.pipeline_runner import EnrichmentPipelineRunner
from engine.enrichment.tech_audit import audit_html_snapshot
from engine.exporters.webhook_exporter import build_webhook_payload, dispatch_webhook
from engine.schemas.campaign import CampaignConfig, EnrichmentLevels, GeoFilter
from engine.schemas.lead import LeadRecord


def test_geo_lock_rejects_clay_ecuador_spain_malta_homonyms():
    geo = GeoFilter(
        country_code="IT",
        region="Sicilia",
        province_code="CT",
        municipalities=["Catania", "Valverde"],
        strict_country_lock=True,
    )
    assert is_within_geo_filter("Desvío Puente Morán Valverde, Pichincha, Ecuador", "Ecuador", geo) is False
    assert is_within_geo_filter("Valverde del Majano, Segovia, Spain", "Spain", geo) is False
    assert is_within_geo_filter("Via Roma 10, 95028 Valverde (CT), Italy", "IT", geo) is True
    assert is_within_geo_filter("Via Etnea 100, 95131 Catania (CT)", "IT", geo) is True


def test_places_connector_normalizes_and_filters_gdo():
    client = PlacesDiscoveryClient()
    campaign = CampaignConfig(
        campaign_id="test_catania",
        name="Test Catania",
        target_vertical="Impianti",
        geo=GeoFilter(country_code="IT", province_code="CT", municipalities=["Catania", "Valverde"]),
        offer_summary="Test",
    )
    ecuador_item = {
        "title": "Tesalia cbc",
        "address": "Desvío Puente Morán Valverde, Ecuador",
        "category": "Food and Beverage Services",
        "phoneNumber": "+593 2 123 4567",
    }
    assert client.normalize_serper_item(ecuador_item, campaign) is None

    gdo_item = {
        "title": "Mediaworld C/O Porte di Catania",
        "address": "Catania (CT)",
        "category": "Elettrodomestici",
    }
    assert client.normalize_serper_item(gdo_item, campaign) is None

    valid_item = {
        "title": "Clima Service Etnea Srl",
        "address": "Via Etnea 12, 95028 Valverde (CT)",
        "category": "Assistenza Caldaie",
        "phoneNumber": "347 1234567",
        "website": "https://www.climaserviceetnea.it/",
        "rating": 4.8,
        "ratingCount": 42,
    }
    rec = client.normalize_serper_item(valid_item, campaign)
    assert rec is not None
    assert rec.phone_e164 == "+393471234567"
    assert rec.phone_type == "Mobile"
    assert rec.postal_code == "95028"
    assert rec.city == "Valverde"


def test_vies_parser_and_luhn_precheck(tmp_path: Path):
    assert parse_vat_identifier("IT 06200390877") == ("IT", "06200390877")
    parsed = ViesValidatorClient.parse_vies_payload(
        "IT",
        "06200390877",
        {
            "isValid": True,
            "name": "SINERGIA RETE D'IMPRESE",
            "address": "PIAZZA DEI MARTIRI 8, CATANIA",
            "requestIdentifier": "WAPI12345",
        },
    )
    assert parsed["is_valid"] is True
    assert parsed["request_identifier"] == "WAPI12345"

    client = ViesValidatorClient(cache_path=tmp_path / "vies_cache.json")
    bad = asyncio.run(client.check_vat("IT06200390878"))
    assert bad["status"] == "INVALID_LUHN"
    assert bad["is_valid"] is False


def test_openapi_parser_and_budget_guard(tmp_path: Path):
    payload = {
        "success": True,
        "data": {
            "companyName": "SINERGIA RETE D'IMPRESE",
            "vatCode": "06200390877",
            "taxCode": "06200390877",
            "activityStatus": "ATTIVA",
            "sdiCode": "MJ1OYNU",
            "atecoClassification": {"atecoCode": "43.22.01", "atecoDescription": "Impianti idraulici"},
            "pec": "SINERGIA@PEC.IT",
            "address": {
                "registeredOffice": {
                    "town": "CATANIA",
                    "province": "CT",
                    "zipCode": "95131",
                    "townCode": "C351",
                    "region": {"description": "SICILIA"},
                }
            },
        },
    }
    parsed = OpenapiItalyClient.parse_company_payload("IT-advanced", payload)
    assert parsed["vat_id"] == "IT06200390877"
    assert parsed["ateco_code"] == "43.22.01"
    assert parsed["cadastral_code"] == "C351"
    assert parsed["pec"] == "sinergia@pec.it"

    client = OpenapiItalyClient(cache_path=tmp_path / "oa_cache.json", max_budget_eur=0.01)
    res_budget = asyncio.run(client.query_company("IT06200390877", endpoint="IT-advanced", use_cache=False))
    assert res_budget["status"] == "BUDGET_EXCEEDED"


def test_tech_audit_html_snapshot_detects_stack_pixels_pec_and_piva():
    html = """
    <html>
      <head>
        <link rel="stylesheet" href="/wp-content/themes/demo/style.css" />
        <script>fbq('init', '123456');</script>
      </head>
      <body>
        <h1>Agenzia Web Catania</h1>
        <a href="https://wa.me/393471234567">Scrivici su WhatsApp</a>
        <a href="https://www.instagram.com/agenzia">IG</a>
        <p>Contattaci a info [at] agenziaweb.it - PEC: agenzia@pec.it - P.IVA IT06200390877</p>
        <form><button>Richiedi un preventivo</button></form>
      </body>
    </html>
    """
    audit = audit_html_snapshot(html, final_url="https://agenziaweb.it", http_status=200)
    assert audit.has_ssl is True
    assert audit.cms_stack == "WordPress"
    assert "Meta Pixel" in audit.tracking_pixels
    assert audit.has_whatsapp_cta is True
    assert audit.has_booking_or_quote_form is True
    assert "info@agenziaweb.it" in audit.emails_found
    assert audit.pec_found == "agenzia@pec.it"
    assert "agenzia@pec.it" not in audit.emails_found
    assert audit.pivas_found == ["06200390877"]
    assert "instagram" in audit.social_links


def test_pipeline_runner_and_webhook_hitl(tmp_path: Path):
    campaign = CampaignConfig(
        campaign_id="camp_test_hitl",
        name="Campagna Test",
        target_vertical="PMI",
        geo=GeoFilter(country_code="IT", province_code="CT"),
        offer_summary="Test offerta",
        enrichment=EnrichmentLevels(
            enable_l1_tech_audit=False,
            enable_l1_mx_check=False,
            enable_l1_vies=False,
            enable_l2_gemini_ai=False,
            enable_l3_openapi_registry=False,
        ),
    )
    seeds = [
        LeadRecord(
            company_name="Agenzia Creativa CT",
            country_code="IT",
            province="CT",
            city="Catania",
            vat_id="IT06200390877",
            phone_e164="+393471112233",
            email="agenzia@pec.it",
            website="https://agenziacreativa.it",
            category="Agenzia Marketing",
        ),
        LeadRecord(
            company_name="Tesalia cbc",
            country_code="EC",
            city="Valverde",
            address="Pichincha, Ecuador",
        ),
    ]
    runner = EnrichmentPipelineRunner()
    res = asyncio.run(runner.run_campaign(campaign, seed_leads=seeds))
    leads = res["leads"]
    assert len(leads) == 1
    lead = leads[0]
    assert lead.ai_qualification.recommended_product == "monetizelab"
    assert lead.lia is not None
    assert lead.lia.status == "PASS"
    assert lead.email == ""
    assert lead.pec == "agenzia@pec.it"

    payload = build_webhook_payload(campaign.campaign_id, leads)
    assert payload["eligible_count"] == 1
    assert payload["contacts"][0]["email"] == ""

    draft_res = asyncio.run(
        dispatch_webhook(campaign.campaign_id, leads, dry_run=True, draft_dir=tmp_path)
    )
    assert draft_res["status"] == "DRAFT_SAVED_FOR_HUMAN_REVIEW"
    assert draft_res["dispatched"] is False
    assert (tmp_path / "webhook_draft_camp_test_hitl.json").exists()
