from engine.routing.product_router import route_lead_to_product


def test_routes_installers_to_tecnicolive():
    res_ateco = route_lead_to_product(
        company_name="Impianti Alfa Srl",
        ateco_code="43.22.01",
    )
    assert res_ateco["product_key"] == "tecnicolive"
    assert res_ateco["product_url"] == "https://www.tecnicolive.it"

    res_kw = route_lead_to_product(
        company_name="Mario Rossi",
        category="Assistenza Caldaie e Climatizzatori",
    )
    assert res_kw["product_key"] == "tecnicolive"


def test_routes_agencies_and_creators_to_monetizelab():
    res_ateco = route_lead_to_product(
        company_name="Studio Blu Srl",
        ateco_code="73.11.01",
    )
    assert res_ateco["product_key"] == "monetizelab"
    assert res_ateco["product_url"] == "https://monetizelab.online"

    res_kw = route_lead_to_product(
        company_name="Etna Social Media Agency",
        category="Digital Marketing & Content Creator",
    )
    assert res_kw["product_key"] == "monetizelab"


def test_routes_generic_smes_to_rsksystem():
    res = route_lead_to_product(
        company_name="Clinica Sorriso Srl",
        category="Studio Dentistico",
        ateco_code="86.23.00",
    )
    assert res["product_key"] == "rsksystem"
    assert res["product_url"] == "https://rsksystem.com"


def test_override_product_wins():
    res = route_lead_to_product(
        company_name="Studio Dentistico",
        override_product="monetizelab",
    )
    assert res["product_key"] == "monetizelab"
