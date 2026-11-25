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
