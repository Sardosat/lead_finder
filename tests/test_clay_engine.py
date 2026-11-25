import pandas as pd

from src.clay_engine import (
    calculate_lead_score,
    enrich_dataset_with_clay_engine,
    extract_semantic_signals,
    generate_dynamic_icebreaker,
)


def test_zero_hallucination_never_invents_brands_or_certs():
    sem = extract_semantic_signals(
        text_corpus="Termoidraulica Rossi Impianti idraulici Catania",
        company_name="Termoidraulica Rossi",
        niche="Termoidraulica & Idraulica",
        website_text="",
    )
    assert sem["marchi_verificati"] is False
    assert sem["marchi"] == []
    assert sem["marchi_str"] == "Non rilevato"
    assert sem["certificazioni"] == "Non rilevate"
    assert sem["is_h24"] is False


def test_extracts_real_brands_from_crawled_website_text():
    sem = extract_semantic_signals(
        text_corpus="Cantarella Clima Catania",
        company_name="Cantarella Clima",
        niche="HVAC & Climatizzazione",
        website_text="Centro assistenza autorizzato Vaillant e Buderus. Reperibilità H24 e rilascio Bollino Blu CITEL.",
    )
    assert sem["marchi_verificati"] is True
    assert "Vaillant" in sem["marchi"]
    assert "Buderus" in sem["marchi"]
    assert sem["is_h24"] is True
    assert "CITEL Sicilia" in sem["certificazioni"]


def test_score_caps_phone_less_and_ignores_portal_urls():
    no_phone_row = {
        "Company Name": "Idraulica Test",
        "Phone": "",
        "Partita_IVA": "IT06200390877",
        "Website": "https://www.pgcasa.it",
        "Stato_CNA": "🔵 NON ASSOCIATO (Target Tesseramento CNA)",
        "Nicchia_Target": "Termoidraulica & Idraulica",
    }
    res_no_ph = calculate_lead_score(no_phone_row)
    assert res_no_ph["has_valid_phone"] is False
    assert res_no_ph["score"] <= 45
    assert "Tier C" in res_no_ph["tier"]

    portal_row = {
        "Company Name": "Idraulica Test",
        "Phone": "+393471234567",
        "Partita_IVA": "IT06200390877",
        "Website": "https://www.pgcasa.it",
        "Stato_CNA": "🔵 NON ASSOCIATO (Target Tesseramento CNA)",
        "Nicchia_Target": "Termoidraulica & Idraulica",
        "Marchi_Verificati": "NO",
    }
    res_portal = calculate_lead_score(portal_row)
    # 25 (mobile) + 20 (piva) + 20 (niche) + 15 (non associato) + 0 (portal URL) + 0 (no verified brand) = 80
    assert res_portal["score"] == 80

    real_web_row = {**portal_row, "Website": "https://www.idraulicatest.it", "Marchi_Verificati": "SI"}
    res_real = calculate_lead_score(real_web_row)
    assert res_real["score"] == 100
    assert "Tier A" in res_real["tier"]


def test_icebreaker_honest_cna_50_percent_and_gdpr_footer():
    df = pd.DataFrame(
        [
            {
                "Company Name": "Termoidraulica Etnea Srl",
                "Nicchia_Target": "Termoidraulica & Idraulica",
                "Category": "Impianti idraulici e termoidraulici",
                "City": "Acireale",
                "Phone": "+393471112233",
                "Partita_IVA": "IT06200390877",
                "Website": "",
                "Stato_CNA": "🔵 NON ASSOCIATO (Target Tesseramento CNA)",
                "Website_Text_Snippet": "",
            }
        ]
    )
    enriched = enrich_dataset_with_clay_engine(df)
    row = enriched.iloc[0]

    assert row["Marchi_Rilevati"] == "Non rilevato"
    assert row["Marchi_Verificati"] == "NO"
    assert "Vaillant" not in row["Icebreaker_1to1"]
    assert "50%" in row["Icebreaker_1to1"]
    assert "15%" not in row["Icebreaker_1to1"]
    assert "CANCELLAMI" in row["Messaggio_WhatsApp_Completo"]
    assert "privacy@tecnicolive.it" in row["Messaggio_WhatsApp_Completo"]
    assert "IT06200390877" in row["Messaggio_WhatsApp_Completo"]
    assert row["Dimensione_Stimata"] == "Società di Capitali (S.r.l. / S.p.A.)"
    assert int(row["Pain_Points_Count"]) >= 1
    assert "TecnicoLIVE" in row["Piano_Consigliato"]


def test_swot_analyzer_detects_meta_pixel_and_company_size():
    from engine.enrichment.swot_analyzer import analyze_lead_swot_and_brief

    res = analyze_lead_swot_and_brief(
        company_name="Clima Tech Etna S.r.l.",
        city="Catania",
        niche="HVAC & Climatizzazione",
        phone_e164="+393471234567",
        phone_type="Mobile",
        website="https://www.climatechetna.it",
        has_valid_piva=True,
        cna_status="NON ASSOCIATO",
        brands=["Daikin", "Vaillant"],
        is_h24=True,
        http_status=200,
        has_ssl=True,
        cms_stack="WordPress",
        tracking_pixels=["Meta Pixel", "Google Analytics 4"],
        has_whatsapp_cta=False,
        has_booking_or_quote_form=False,
        employees_count=12,
        recommended_product="tecnicolive",
        recommended_product_name="TecnicoLIVE",
    )

    strength_ids = {s.id for s in res["strengths"]}
    pain_ids = {p.id for p in res["pain_signals"]}
    weak_ids = {w.id for w in res["weak_points"]}

    assert "str_ads_active" in strength_ids
    assert "str_structured" in strength_ids
    assert "str_brands" in strength_ids
    assert "pain_ads_leak" in pain_ids
    assert "pain_h24_missed" in pain_ids
    assert "weak_no_wa" in weak_ids
    assert "Meta Pixel" in res["sales_brief"].why_sell
    assert "12 dipendenti" in res["company_size_label"]
    assert "Business" in res["sales_brief"].recommended_plan
