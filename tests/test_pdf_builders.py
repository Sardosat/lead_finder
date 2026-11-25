import pandas as pd

from src.generate_pdf_report import build_html_report
from src.generate_termoidraulica_pdf import build_termoidraulica_html
from src.generate_top100_pdf import build_top100_html, select_top100_callable


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Company Name": 'Clima <script>alert("xss")</script> & Co',
                "Nicchia_Target": "Termoidraulica & Idraulica",
                "City": "Catania",
                "Area_Geografica": "Area Metropolitana",
                "Phone": "+393471234567",
                "Partita_IVA": "IT06200390877",
                "Stato_CNA": "🔵 NON ASSOCIATO (Target Tesseramento CNA)",
                "ICP_Score": "95",
                "Lead_Tier": "Tier A 🔥 (VIP / Priorità Immediata)",
                "Marchi_Rilevati": "Vaillant",
                "Marchi_Verificati": "SI",
                "Icebreaker_1to1": 'Test & "quote"',
                "Evidenza_CNA": "",
            },
            {
                "Company Name": "Idraulica Senza Telefono",
                "Nicchia_Target": "Termoidraulica & Idraulica",
                "City": "Acireale",
                "Area_Geografica": "Distretto Acese",
                "Phone": "",
                "Partita_IVA": "IT06200390877",
                "Stato_CNA": "🟡 DA VERIFICARE (P.IVA mancante)",
                "ICP_Score": "40",
                "Lead_Tier": "Tier C ❄️ (Cold / Da Arricchire)",
                "Marchi_Rilevati": "Non rilevato",
                "Marchi_Verificati": "NO",
                "Icebreaker_1to1": "Gancio onesto",
                "Evidenza_CNA": "",
            },
        ]
    )


def test_pdf_builders_escape_html_and_use_official_pricing():
    df = _sample_df()

    html_strat = build_html_report(
        stats={
            "totale": 2,
            "chiamabili": 1,
            "da_arricchire": 1,
            "piva_valide": 2,
            "associati_cna": 0,
            "target_nuovi": 1,
            "target_chiamabili": 1,
        },
        associati=[],
        top_targets=df.iloc[:1].to_dict(orient="records"),
        niche_counts={"Termoidraulica & Idraulica": 2},
    )
    assert "<script>alert" not in html_strat
    assert "&lt;script&gt;" in html_strat
    assert "269" in html_strat
    assert "599" in html_strat
    assert "50%" in html_strat
    assert "STIMA TEORICA" in html_strat

    html_termo = build_termoidraulica_html(df)
    assert "<script>alert" not in html_termo
    assert "&lt;script&gt;" in html_termo
    assert "50%" in html_termo
    assert "696 imprese" not in html_termo.lower()

    top100 = select_top100_callable(df)
    assert len(top100) == 1
    assert top100.iloc[0]["Phone"] == "+393471234567"

    html_top = build_top100_html(top100)
    assert "<script>alert" not in html_top
    assert "Top 1 Lead" in html_top
    assert "STIMA TEORICA" in html_top
    assert "269€" in html_top
    assert "298K€" not in html_top
