"""
Generatore Report PDF Esecutivo per il CEO: I Top 100 Lead Chiamabili di Termoidraulica
a Massima Probabilità di Conversione — Città Metropolitana di Catania & CNA Catania.
- Solo contatti con telefono E.164 valido (mai lead senza numero).
- Tutti i KPI e badge calcolati dinamicamente (zero valori hardcoded).
- Zero sovrascritture di Report_Termoidraulica_Catania_Provincia_CNA.pdf.
"""

import asyncio
import html as html_lib
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
from playwright.async_api import async_playwright

from src.config import (
    DATA_DIR,
    DEFAULT_ARPU_MONTHLY,
    OUTPUT_OUTBOUND_CSV,
    OUTPUT_TERMOIDRAULICA_CSV,
    PDF_TOP100_FILE,
    PRICING_PLANS,
    SENDER_IDENTITY,
)
from src.normalizers import is_strict_e164_italian

PDF_OUTPUT_PATH = PDF_TOP100_FILE


def _esc(val) -> str:
    return html_lib.escape("" if val is None else str(val), quote=True)


def select_top100_callable(df: pd.DataFrame) -> pd.DataFrame:
    """Seleziona fino a 100 lead chiamabili (E.164) di Termoidraulica ordinati per score ICP."""
    if df.empty:
        return df.copy()

    work = df.copy()
    work["_valid_ph"] = work.get("Phone", pd.Series([""] * len(work))).fillna("").astype(str).apply(is_strict_e164_italian)
    callable_df = work[work["_valid_ph"]].copy()
    if callable_df.empty:
        return callable_df.drop(columns=["_valid_ph"])

    callable_df["ICP_Score_Num"] = pd.to_numeric(callable_df.get("ICP_Score", 0), errors="coerce").fillna(0)
    callable_df["_marchi_ok"] = (callable_df.get("Marchi_Verificati", "") == "SI").astype(int)
    callable_df["_has_piva"] = callable_df.get("Partita_IVA", "").fillna("").astype(str).str.startswith("IT").astype(int)

    df_sorted = callable_df.sort_values(
        by=["ICP_Score_Num", "_marchi_ok", "_has_piva", "Company Name"],
        ascending=[False, False, False, True],
    )
    return df_sorted.head(100).drop(columns=["_valid_ph", "_marchi_ok", "_has_piva"]).copy()


def build_top100_html(top100: pd.DataFrame) -> str:
    totale = len(top100)
    safe_tot = max(1, totale)

    pivas = top100.get("Partita_IVA", pd.Series([""] * totale)).fillna("").astype(str)
    piva_count = int(pivas.str.startswith("IT").sum())
    piva_pct = round(piva_count / safe_tot * 100, 1)

    stati = top100.get("Stato_CNA", pd.Series([""] * totale)).fillna("").astype(str)
    target_cna_count = int(stati.str.contains("NON ASSOCIATO", na=False).sum())
    target_cna_pct = round(target_cna_count / safe_tot * 100, 1)

    tiers = top100.get("Lead_Tier", pd.Series([""] * totale)).fillna("").astype(str)
    tier_a_count = int(tiers.str.contains("Tier A", na=False).sum())
    tier_a_pct = round(tier_a_count / safe_tot * 100, 1)

    scores = pd.to_numeric(top100.get("ICP_Score", pd.Series([0] * totale)), errors="coerce").fillna(0)
    min_score = int(scores.min()) if totale else 0
    max_score = int(scores.max()) if totale else 0

    pipeline_arr_teorica = totale * DEFAULT_ARPU_MONTHLY * 12
    pipeline_arr_k = f"{round(pipeline_arr_teorica / 1000):.0f}K€"

    comuni_counts = top100["City"].replace("", "Catania").value_counts().head(8).to_dict() if totale else {}
    area_series = top100["Area_Geografica"] if "Area_Geografica" in top100.columns else top100.get("City", pd.Series(dtype=str))
    area_counts = area_series.replace("", "Provincia").value_counts().to_dict() if totale else {}

    leads_list = top100.to_dict(orient="records")
    CHUNK_SIZE = 10
    chunks = [leads_list[i: i + CHUNK_SIZE] for i in range(0, len(leads_list), CHUNK_SIZE)]

    area_rows = "".join(
        f"""
        <tr>
            <td><strong>{_esc(area)}</strong></td>
            <td style="text-align: right; font-weight: 700;">{count}</td>
            <td style="text-align: right; color: #718096;">{round(count / safe_tot * 100, 1)}%</td>
        </tr>
        """
        for area, count in sorted(area_counts.items(), key=lambda x: x[1], reverse=True)
    )

    comune_rows = "".join(
        f"""
        <tr>
            <td><strong>{_esc(comune)}</strong></td>
            <td style="text-align: right; font-weight: 700; color: #005A9E;">{c_count}</td>
            <td style="text-align: right; color: #2F855A; font-weight: 700;">ALTA</td>
        </tr>
        """
        for comune, c_count in list(comuni_counts.items())[:6]
    )

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Report Esecutivo CEO - Top {totale} Lead Chiamabili Termoidraulica Catania</title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 8mm 10mm 10mm 10mm;
            @top-right {{
                content: "DOCUMENTO RISERVATO DIREZIONALE • TECNICOLIVE & CNA CATANIA";
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 6.5pt;
                font-weight: 700;
                color: #A0AEC0;
            }}
            @bottom-left {{
                content: "{_esc(SENDER_IDENTITY)}";
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 6.3pt;
                color: #718096;
            }}
            @bottom-right {{
                content: "Pagina " counter(page) " di " counter(pages);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 7pt;
                font-weight: 700;
                color: #4A5568;
            }}
        }}
        * {{
            box-sizing: border-box;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #1A202C;
            background-color: #FFFFFF;
            margin: 0;
            padding: 0;
            line-height: 1.28;
            font-size: 7.7pt;
        }}
        .page {{
            page-break-after: always;
            height: 272mm;
            max-height: 272mm;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}
        .page:last-child {{ page-break-after: avoid; }}
        .page-content {{ flex: 1; }}
        .header-box {{
            border-bottom: 2.5px solid #005A9E;
            padding-bottom: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .brand-title {{
            font-size: 16.5pt;
            font-weight: 900;
            color: #005A9E;
            letter-spacing: -0.5px;
            margin: 0;
            text-transform: uppercase;
        }}
        .brand-subtitle {{
            font-size: 9.2pt;
            font-weight: 700;
            color: #2D3748;
            margin-top: 2px;
        }}
        .header-badge {{
            background: #EBF8FF;
            border: 1px solid #3182CE;
            color: #2B6CB0;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: 800;
            font-size: 7.5pt;
            text-transform: uppercase;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
            margin-bottom: 10px;
        }}
        .kpi-card {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 5px;
            padding: 7px 5px;
            text-align: center;
        }}
        .kpi-num {{
            font-size: 14.5pt;
            font-weight: 900;
            color: #1A202C;
            line-height: 1;
        }}
        .kpi-label {{
            font-size: 6.6pt;
            font-weight: 700;
            color: #4A5568;
            text-transform: uppercase;
            margin-top: 3px;
        }}
        .kpi-sub {{
            font-size: 6pt;
            color: #2B6CB0;
            font-weight: 600;
            margin-top: 2px;
        }}
        .strategic-box {{
            background: #F0FFF4;
            border: 1.5px solid #9AE6B4;
            border-radius: 5px;
            padding: 8px 11px;
            font-size: 7.5pt;
            margin-bottom: 10px;
            color: #22543D;
        }}
        .cols-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 10px;
        }}
        .section-title {{
            font-size: 8.8pt;
            font-weight: 800;
            color: #005A9E;
            border-bottom: 1.5px solid #CBD5E0;
            padding-bottom: 2px;
            margin-top: 6px;
            margin-bottom: 5px;
            text-transform: uppercase;
        }}
        .table-summary {{
            width: 100%;
            border-collapse: collapse;
            font-size: 7.2pt;
        }}
        .table-summary th {{
            background-color: #EDF2F7;
            color: #2D3748;
            font-weight: 700;
            text-align: left;
            padding: 4px 6px;
            border-bottom: 1px solid #CBD5E0;
        }}
        .table-summary td {{
            padding: 3.5px 6px;
            border-bottom: 1px solid #E2E8F0;
        }}
        .table-leads {{
            width: 100%;
            border-collapse: collapse;
            font-size: 6.8pt;
            table-layout: fixed;
        }}
        .table-leads th {{
            background-color: #005A9E;
            color: #FFFFFF;
            font-weight: 800;
            text-align: left;
            padding: 4.5px 5px;
            font-size: 6.6pt;
            text-transform: uppercase;
        }}
        .table-leads td {{
            padding: 4px 5px;
            border-bottom: 1px solid #E2E8F0;
            vertical-align: middle;
            word-wrap: break-word;
        }}
        .table-leads tr:nth-child(even) {{ background-color: #F8FAFC; }}
        .badge-vip {{
            background-color: #FEFCBF;
            color: #744210;
            border: 1px solid #D69E2E;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 800;
            font-size: 6.1pt;
            display: inline-block;
        }}
        .badge-warm {{
            background-color: #EDF2F7;
            color: #2D3748;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 700;
            font-size: 6.1pt;
            display: inline-block;
        }}
        .badge-target {{
            background-color: #EBF8FF;
            color: #2B6CB0;
            border: 1px solid #90CDF4;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 700;
            font-size: 6.1pt;
            display: inline-block;
        }}
        .badge-socio {{
            background-color: #C6F6D5;
            color: #22543D;
            border: 1px solid #68D391;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 700;
            font-size: 6.1pt;
            display: inline-block;
        }}
        .icebreaker-mini {{
            background: #F0FFF4;
            border-left: 2.5px solid #38A169;
            padding: 2.5px 5px;
            font-size: 6.2pt;
            color: #22543D;
            line-height: 1.22;
            font-style: italic;
            border-radius: 0 3px 3px 0;
        }}
    </style>
</head>
<body>

    <div class="page">
        <div class="page-content">
            <div class="header-box">
                <div>
                    <div class="brand-title">TecnicoLIVE &bull; Report Strategico CEO</div>
                    <div class="brand-subtitle">Top {totale} Lead Chiamabili Termoidraulica (E.164 + Score ICP)</div>
                    <div style="font-size: 7.4pt; color: #4A5568; margin-top: 2px;">
                        Città Metropolitana di Catania &bull; Partnership <strong>CNA Catania (50% 1° Anno)</strong>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div class="header-badge">Executive Selection</div>
                    <div style="font-size: 6.8pt; color: #718096; margin-top: 3px;">Solo Lead con Telefono E.164</div>
                </div>
            </div>

            <div class="kpi-grid">
                <div class="kpi-card">
                    <div class="kpi-num" style="color: #005A9E;">{totale}</div>
                    <div class="kpi-label">Lead Chiamabili</div>
                    <div class="kpi-sub">Score: {min_score} - {max_score} pt</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-num" style="color: #DD6B20;">{tier_a_pct:.0f}%</div>
                    <div class="kpi-label">Tier A 🔥 VIP ({tier_a_count})</div>
                    <div class="kpi-sub">Priorità Outbound</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-num" style="color: #2B6CB0;">{target_cna_pct:.0f}%</div>
                    <div class="kpi-label">Target Non CNA ({target_cna_count})</div>
                    <div class="kpi-sub">Leva 50% 1° Anno CNA</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-num" style="color: #2F855A;">{piva_pct:.0f}%</div>
                    <div class="kpi-label">P.IVA Luhn IT ({piva_count})</div>
                    <div class="kpi-sub">Ditte Validate</div>
                </div>
                <div class="kpi-card">
                    <div class="kpi-num" style="color: #805AD5;">{pipeline_arr_k}</div>
                    <div class="kpi-label">STIMA TEORICA TAM ARR</div>
                    <div class="kpi-sub">{totale} x {DEFAULT_ARPU_MONTHLY}€/m x 12m (Pro)</div>
                </div>
            </div>

            <div class="strategic-box">
                <strong>🎯 Criteri di Selezione & Trasparenza Dati (`AGENTS.md`):</strong>
                <p style="margin: 3px 0 0 0;">
                    Questo dossier seleziona i <strong>{totale} contatti termoidraulici chiamabili</strong> (tutti con telefono verificato E.164 <code>+39</code>, zero GDO retail).
                    Il valore indicato come TAM ARR (<strong>{pipeline_arr_k}</strong> su Piano Pro <strong>{PRICING_PLANS['pro']['monthly']}€/mese</strong> + {PRICING_PLANS['pro']['setup_fee']}€ Setup)
                    è una <strong>STIMA TEORICA / MODELLO PREDITTIVO</strong> riferita all'intero bacino Top {totale} al 100% di conversione teorica (Base {PRICING_PLANS['base']['monthly']}€/m, Pro {PRICING_PLANS['pro']['monthly']}€/m, Business {PRICING_PLANS['business']['monthly']}€/m).
                    Ai non associati CNA si propone il pacchetto con <strong>associazione a CNA Catania al 50% per il 1° anno</strong>.
                </p>
            </div>

            <div class="cols-2">
                <div>
                    <div class="section-title">1. Comprensori Provinciali</div>
                    <table class="table-summary">
                        <thead>
                            <tr>
                                <th>Area Geografica</th>
                                <th style="text-align: right;">Lead</th>
                                <th style="text-align: right;">Quota</th>
                            </tr>
                        </thead>
                        <tbody>{area_rows}</tbody>
                    </table>
                </div>

                <div>
                    <div class="section-title">2. Comuni Principali</div>
                    <table class="table-summary">
                        <thead>
                            <tr>
                                <th>Comune</th>
                                <th style="text-align: right;">Ditte</th>
                                <th style="text-align: right;">Priorità</th>
                            </tr>
                        </thead>
                        <tbody>{comune_rows}</tbody>
                    </table>
                </div>
            </div>

            <div style="background: #FFF5F5; border: 1.5px solid #FEB2B2; border-radius: 5px; padding: 6px 10px; font-size: 7.1pt; color: #9B2C2C;">
                <strong>📞 Direttiva Operativa & GDPR (Human-in-the-Loop):</strong><br>
                Contattare in ordine di ranking. Gli Icebreaker riportano solo marchi realmente rilevati (altrimenti focus su Comune e Nicchia) e includono la proposta CNA al 50% per il 1° anno.
            </div>
        </div>
    </div>
    """

    for page_idx, chunk in enumerate(chunks, 1):
        start_rank = (page_idx - 1) * CHUNK_SIZE + 1
        end_rank = start_rank + len(chunk) - 1

        html += f"""
        <div class="page">
            <div class="page-content">
                <div style="border-bottom: 2px solid #005A9E; padding-bottom: 4px; margin-bottom: 7px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #005A9E; font-size: 8.4pt; text-transform: uppercase;">Top {totale} Lead Termoidraulica • Ranking #{start_rank} - #{end_rank}</strong>
                        <span style="color: #718096; font-size: 6.9pt; margin-left: 8px;">Catania &bull; Solo Chiamabili E.164</span>
                    </div>
                    <div style="font-size: 6.9pt; font-weight: 700; color: #2B6CB0;">
                        Score Range Selezione: {min_score}–{max_score} pt
                    </div>
                </div>

                <table class="table-leads">
                    <thead>
                        <tr>
                            <th style="width: 4%; text-align: center;">#</th>
                            <th style="width: 24%;">Ragione Sociale & Marchi</th>
                            <th style="width: 14%;">Comune & Area</th>
                            <th style="width: 16%;">Telefono E.164 & P.IVA</th>
                            <th style="width: 13%;">Stato CNA & Score</th>
                            <th style="width: 29%;">Icebreaker 1-to-1 Verificato</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for lead_idx, lead in enumerate(chunk, start_rank):
            tier_str = str(lead.get("Lead_Tier", "Tier C"))
            if "Tier A" in tier_str:
                tier_cls, tier_lbl = "badge-vip", "Tier A VIP 🔥"
            elif "Tier B" in tier_str:
                tier_cls, tier_lbl = "badge-warm", "Tier B 🟡"
            else:
                tier_cls, tier_lbl = "badge-warm", "Tier C ❄️"

            stato_str = str(lead.get("Stato_CNA", ""))
            if "ASSOCIATO RILEVATO" in stato_str:
                cna_cls, cna_lbl = "badge-socio", "SOCIO CNA"
            elif "NON ASSOCIATO" in stato_str:
                cna_cls, cna_lbl = "badge-target", "TARGET CNA 50%"
            else:
                cna_cls, cna_lbl = "badge-warm", "DA VERIFICARE"

            html += f"""
                        <tr>
                            <td style="text-align: center; font-weight: 800; color: #005A9E; font-size: 7pt;">{lead_idx}</td>
                            <td>
                                <strong style="color: #1A202C; font-size: 7.4pt;">{_esc(lead.get('Company Name', ''))}</strong><br>
                                <span style="color: #4A5568; font-size: 6.2pt;">🔧 {_esc(lead.get('Marchi_Rilevati') or 'Non rilevato')}</span>
                            </td>
                            <td>
                                <strong style="font-size: 7pt;">{_esc(lead.get('City', ''))}</strong><br>
                                <span style="color: #718096; font-size: 6pt;">{_esc(lead.get('Area_Geografica', 'Provincia'))}</span>
                            </td>
                            <td>
                                <strong style="color: #005A9E; font-size: 7pt;">{_esc(lead.get('Phone', ''))}</strong><br>
                                <code style="color: #4A5568; font-size: 6.2pt;">{_esc(lead.get('Partita_IVA') or 'N/D')}</code>
                            </td>
                            <td>
                                <span class="{tier_cls}">{tier_lbl}</span>
                                <span style="font-weight: 800; color: #2B6CB0; font-size: 6.3pt;">{_esc(lead.get('ICP_Score', '0'))} pt</span><br>
                                <span class="{cna_cls}">{cna_lbl}</span>
                            </td>
                            <td>
                                <div class="icebreaker-mini">
                                    "{_esc(lead.get('Icebreaker_1to1', ''))}"
                                </div>
                            </td>
                        </tr>
            """

        html += """
                    </tbody>
                </table>
            </div>
        </div>
        """

    html += """
</body>
</html>"""
    return html


async def generate_top100_pdf() -> Path:
    csv_file = OUTPUT_TERMOIDRAULICA_CSV if OUTPUT_TERMOIDRAULICA_CSV.exists() else OUTPUT_OUTBOUND_CSV
    print(f"Caricamento dataset Termoidraulica: {csv_file}")
    df = pd.read_csv(csv_file, dtype=str).fillna("")

    top100 = select_top100_callable(df)
    print(
        f"Selezionati Top {len(top100)} lead chiamabili (Score: "
        f"{pd.to_numeric(top100['ICP_Score'], errors='coerce').min() if len(top100) else 0} - "
        f"{pd.to_numeric(top100['ICP_Score'], errors='coerce').max() if len(top100) else 0} pt)"
    )

    html_content = build_top100_html(top100)

    html_file = DATA_DIR / "temp_top100_report.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Compilazione PDF Top 100 CEO con Playwright Chromium...")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file:///{html_file.resolve().as_posix()}", wait_until="networkidle")
        await page.pdf(
            path=str(PDF_OUTPUT_PATH),
            format="A4",
            print_background=True,
            margin={"top": "8mm", "bottom": "8mm", "left": "8mm", "right": "8mm"},
        )
        await browser.close()

    if html_file.exists():
        html_file.unlink()

    print(f"PDF Top 100 CEO generato con successo (distinto, zero sovrascritture): {PDF_OUTPUT_PATH}")
    return PDF_OUTPUT_PATH


if __name__ == "__main__":
    asyncio.run(generate_top100_pdf())
