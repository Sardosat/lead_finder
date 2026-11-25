"""
Generatore Report PDF Esecutivo Completo per il CEO
Censimento Integrale Impiantistica & Termoidraulica Catania & Provincia (Tutti i 58 Comuni)
Include tutte le ditte pulite e deduplicate del verticale con P.IVA, telefoni E.164,
Stato CNA, ICP Score, marchi reali verificati e Icebreaker 1-to-1 onesti.
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
    OUTPUT_OUTBOUND_CSV,
    OUTPUT_TERMOIDRAULICA_CSV,
    PDF_TERMOIDRAULICA_FILE,
    SENDER_IDENTITY,
)

PDF_OUTPUT_PATH = PDF_TERMOIDRAULICA_FILE


def _esc(val) -> str:
    return html_lib.escape("" if val is None else str(val), quote=True)


def build_termoidraulica_html(df: pd.DataFrame) -> str:
    totale = len(df)
    safe_tot = max(1, totale)

    phones = df.get("Phone", pd.Series([""] * totale)).fillna("").astype(str)
    chiamabili = int((phones.str.strip() != "").sum())
    cellulari = int(phones.str.contains(r"^\+393", regex=True, na=False).sum())
    da_arricchire = totale - chiamabili

    pivas = df.get("Partita_IVA", pd.Series([""] * totale)).fillna("").astype(str)
    piva_valide = int(pivas.str.startswith("IT").sum())
    perc_piva = round((piva_valide / safe_tot * 100), 1)

    stati = df.get("Stato_CNA", pd.Series([""] * totale)).fillna("").astype(str)
    associati = int(stati.str.contains("ASSOCIATO RILEVATO", na=False).sum())
    target_cna = int(stati.str.contains("NON ASSOCIATO", na=False).sum())

    tiers = df.get("Lead_Tier", pd.Series([""] * totale)).fillna("").astype(str)
    tier_a = int(tiers.str.contains("Tier A", na=False).sum())
    tier_b = int(tiers.str.contains("Tier B", na=False).sum())
    tier_c = int(tiers.str.contains("Tier C", na=False).sum())

    area_series = df["Area_Geografica"] if "Area_Geografica" in df.columns else df["City"]
    area_counts = area_series.replace("", "Provincia").value_counts().to_dict()
    top_comuni = df["City"].replace("", "Catania").value_counts().head(10).to_dict()

    # Conta solo marchi realmente rilevati (Zero Hallucination)
    marchi_col = df.get("Marchi_Rilevati", pd.Series([""] * totale)).fillna("").astype(str)
    marchi_stats = {}
    for brand in ("Vaillant", "Baxi", "Buderus", "Bosch", "Ariston", "Immergas", "Daikin", "Mitsubishi", "Ferroli", "Fujitsu"):
        cnt = int(marchi_col.str.contains(brand, case=False, na=False).sum())
        if cnt > 0:
            marchi_stats[brand] = cnt
    if not marchi_stats:
        marchi_stats = {"Marchi verificati da crawl/nome": int((df.get("Marchi_Verificati", pd.Series(["NO"] * totale)) == "SI").sum())}

    df_sorted = df.copy()
    df_sorted["_call"] = (phones.str.strip() != "").astype(int)
    df_sorted["ICP_Score_Num"] = pd.to_numeric(df_sorted.get("ICP_Score", 0), errors="coerce").fillna(0)
    df_sorted = df_sorted.sort_values(
        by=["_call", "ICP_Score_Num", "Company Name"],
        ascending=[False, False, True],
    )
    all_leads = df_sorted.to_dict(orient="records")

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

    marchi_rows = "".join(
        f"""
        <tr>
            <td><strong>{_esc(m_name)}</strong> (rilevato su nome/sito reale)</td>
            <td style="text-align: right; font-weight: 700;">{m_cnt}</td>
            <td style="text-align: right; color: #2B6CB0;">{round(m_cnt / safe_tot * 100, 1)}%</td>
        </tr>
        """
        for m_name, m_cnt in sorted(marchi_stats.items(), key=lambda x: x[1], reverse=True)[:6]
    )

    lead_rows_html = []
    for idx, lead in enumerate(all_leads, 1):
        tier_str = str(lead.get("Lead_Tier", "Tier C"))
        if "Tier A" in tier_str:
            tier_cls = "badge-vip"
            tier_short = "Tier A VIP 🔥"
        elif "Tier B" in tier_str:
            tier_cls = "badge-warm"
            tier_short = "Tier B 🟡"
        else:
            tier_cls = "badge-cold"
            tier_short = "Tier C ❄️"

        stato_str = str(lead.get("Stato_CNA", ""))
        if "ASSOCIATO RILEVATO" in stato_str:
            cna_cls = "badge-socio"
            cna_label = "SOCIO CNA"
        elif "NON ASSOCIATO" in stato_str:
            cna_cls = "badge-target"
            cna_label = "TARGET CNA 50%"
        else:
            cna_cls = "badge-warm"
            cna_label = "DA VERIFICARE"

        phone_disp = lead.get("Phone") or "Da arricchire"
        marchi_disp = lead.get("Marchi_Rilevati") or "Non rilevato"
        lead_rows_html.append(
            f"""
            <tr>
                <td style="text-align: center; color: #718096; font-size: 6.5pt;">{idx}</td>
                <td>
                    <strong style="color: #1A202C; font-size: 7.4pt;">{_esc(lead.get('Company Name', ''))}</strong><br>
                    <span style="color: #4A5568; font-size: 6.3pt;">🔧 {_esc(marchi_disp)}</span>
                </td>
                <td>
                    <strong>{_esc(lead.get('City', ''))}</strong><br>
                    <span style="color: #718096; font-size: 6.3pt;">{_esc(lead.get('Area_Geografica', 'Provincia'))}</span>
                </td>
                <td>
                    <strong style="color: #005A9E;">{_esc(phone_disp)}</strong><br>
                    <code style="color: #4A5568; font-size: 6.3pt;">{_esc(lead.get('Partita_IVA') or 'N/D')}</code>
                </td>
                <td>
                    <span class="{tier_cls}">{tier_short}</span>
                    <span style="font-weight: 700; color: #2B6CB0; font-size: 6.5pt;">({ _esc(lead.get('ICP_Score', '0')) } pt)</span><br>
                    <span class="{cna_cls}">{cna_label}</span>
                </td>
                <td>
                    <div class="icebreaker-mini">
                        "{_esc(lead.get('Icebreaker_1to1', ''))}"
                    </div>
                </td>
            </tr>
            """
        )

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Censimento Ufficiale Termoidraulica Catania & Provincia - Ad Uso del CEO</title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 10mm 10mm 12mm 10mm;
            @top-right {{
                content: "DOCUMENTO RISERVATO DIREZIONALE - TECNICOLIVE & CNA CATANIA";
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 6.5pt;
                font-weight: 700;
                color: #A0AEC0;
            }}
            @bottom-left {{
                content: "{_esc(SENDER_IDENTITY)}";
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 6.5pt;
                color: #718096;
            }}
            @bottom-right {{
                content: "Pagina " counter(page) " di " counter(pages);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 7.5pt;
                font-weight: 600;
                color: #4A5568;
            }}
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #1A202C;
            background-color: #FFFFFF;
            margin: 0;
            padding: 0;
            line-height: 1.35;
            font-size: 8pt;
        }}
        .cover-page {{
            page-break-after: always;
            padding-top: 12px;
        }}
        .header-box {{
            border-bottom: 3px solid #005A9E;
            padding-bottom: 10px;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .brand-title {{
            font-size: 19pt;
            font-weight: 900;
            color: #005A9E;
            letter-spacing: -0.5px;
            margin: 0;
            text-transform: uppercase;
        }}
        .brand-subtitle {{
            font-size: 10pt;
            font-weight: 700;
            color: #2D3748;
            margin-top: 4px;
        }}
        .header-badge {{
            background: #EBF8FF;
            border: 1px solid #3182CE;
            color: #2B6CB0;
            padding: 4px 10px;
            border-radius: 4px;
            font-weight: 800;
            font-size: 7.8pt;
            text-transform: uppercase;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
            margin-bottom: 14px;
        }}
        .kpi-card {{
            background: #F7FAFC;
            border: 1.5px solid #E2E8F0;
            border-radius: 6px;
            padding: 9px 6px;
            text-align: center;
        }}
        .kpi-num {{
            font-size: 16pt;
            font-weight: 900;
            color: #1A202C;
            line-height: 1;
        }}
        .kpi-label {{
            font-size: 6.8pt;
            font-weight: 700;
            color: #4A5568;
            text-transform: uppercase;
            margin-top: 4px;
        }}
        .kpi-sub {{
            font-size: 6.4pt;
            color: #2B6CB0;
            font-weight: 600;
            margin-top: 2px;
        }}
        .section-title {{
            font-size: 10pt;
            font-weight: 800;
            color: #005A9E;
            border-bottom: 1.5px solid #CBD5E0;
            padding-bottom: 3px;
            margin-top: 12px;
            margin-bottom: 8px;
            text-transform: uppercase;
        }}
        .cols-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 12px;
        }}
        .table-summary {{
            width: 100%;
            border-collapse: collapse;
            font-size: 7.5pt;
        }}
        .table-summary th {{
            background-color: #EDF2F7;
            color: #2D3748;
            font-weight: 700;
            text-align: left;
            padding: 5px 6px;
            border-bottom: 1.5px solid #CBD5E0;
        }}
        .table-summary td {{
            padding: 4px 6px;
            border-bottom: 1px solid #E2E8F0;
        }}
        .strategic-box {{
            background: #F0FFF4;
            border: 1.5px solid #9AE6B4;
            border-radius: 6px;
            padding: 9px 12px;
            font-size: 7.8pt;
            margin-bottom: 12px;
            color: #22543D;
        }}
        .table-leads {{
            width: 100%;
            border-collapse: collapse;
            font-size: 6.9pt;
            margin-top: 8px;
        }}
        thead {{ display: table-header-group; }}
        tr {{ page-break-inside: avoid; }}
        .table-leads th {{
            background-color: #005A9E;
            color: #FFFFFF;
            font-weight: 800;
            text-align: left;
            padding: 5px 6px;
            font-size: 6.7pt;
            text-transform: uppercase;
        }}
        .table-leads td {{
            padding: 4px 5px;
            border-bottom: 1px solid #E2E8F0;
            vertical-align: top;
        }}
        .table-leads tr:nth-child(even) {{ background-color: #F8FAFC; }}
        .badge-vip {{
            background-color: #FEFCBF;
            color: #744210;
            border: 1px solid #D69E2E;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 800;
            font-size: 6.3pt;
            display: inline-block;
        }}
        .badge-warm {{
            background-color: #EDF2F7;
            color: #2D3748;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 600;
            font-size: 6.3pt;
            display: inline-block;
        }}
        .badge-cold {{
            background-color: #F7FAFC;
            color: #718096;
            border: 1px solid #CBD5E0;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 600;
            font-size: 6.3pt;
            display: inline-block;
        }}
        .badge-target {{
            background-color: #EBF8FF;
            color: #2B6CB0;
            border: 1px solid #90CDF4;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 700;
            font-size: 6.2pt;
            display: inline-block;
        }}
        .badge-socio {{
            background-color: #C6F6D5;
            color: #22543D;
            border: 1px solid #68D391;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 700;
            font-size: 6.2pt;
            display: inline-block;
        }}
        .icebreaker-mini {{
            background: #F0FFF4;
            border-left: 2px solid #38A169;
            padding: 3px 5px;
            font-size: 6.4pt;
            color: #22543D;
            line-height: 1.25;
            font-style: italic;
            border-radius: 0 3px 3px 0;
        }}
    </style>
</head>
<body>

    <div class="cover-page">
        <div class="header-box">
            <div>
                <div class="brand-title">TecnicoLIVE &bull; Executive Report</div>
                <div class="brand-subtitle">Censimento & Qualificazione Integrale Impiantistica Termoidraulica & Clima</div>
                <div style="font-size: 7.8pt; color: #4A5568; margin-top: 3px;">
                    Ambito: <strong>Città Metropolitana di Catania (58 Comuni)</strong> &bull; Convenzione <strong>CNA Catania (50% 1° Anno)</strong>
                </div>
            </div>
            <div style="text-align: right;">
                <div class="header-badge">Catalogo Integrale CEO</div>
                <div style="font-size: 7.2pt; color: #718096; margin-top: 4px;">P.IVA IT06200390877</div>
                <div style="font-size: 7.2pt; color: #718096;">Piazza dei Martiri 8, Catania</div>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-num">{totale}</div>
                <div class="kpi-label">Imprese Pulite</div>
                <div class="kpi-sub">{chiamabili} chiamabili ({cellulari} mob)</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num" style="color: #2B6CB0;">{target_cna}</div>
                <div class="kpi-label">Target Non Associati</div>
                <div class="kpi-sub">Leva CNA 50% 1° Anno</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num" style="color: #DD6B20;">{tier_a}</div>
                <div class="kpi-label">Tier A 🔥 VIP</div>
                <div class="kpi-sub">Score &ge; 80 + E.164</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num" style="color: #4A5568;">{tier_b}</div>
                <div class="kpi-label">Tier B 🟡 Warm</div>
                <div class="kpi-sub">{tier_c} Tier C ({da_arricchire} no tel)</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num" style="color: #2F855A;">{piva_valide}</div>
                <div class="kpi-label">P.IVA Validate Luhn</div>
                <div class="kpi-sub">{perc_piva}% Fiscale Certificato</div>
            </div>
        </div>

        <div class="strategic-box">
            <strong>🎯 Sintesi Esecutiva & Igiene Dati (Zero Hallucination):</strong>
            <p style="margin: 4px 0 0 0;">
                Il catalogo raccoglie tutte le <strong>{totale} imprese pulite</strong> del verticale Termoidraulica & Clima (escluse GDO e record esteri),
                suddivise in <strong>{chiamabili} contatti immediatamente chiamabili (formato E.164 +39)</strong> e <strong>{da_arricchire} schede isolate in <code>da_arricchire_contatti.csv</code></strong>.
                Per i non associati ({target_cna} ditte) l'offerta commerciale abbina i piani TecnicoLIVE (Base 169€, Pro 269€, Business 369€)
                all'<strong>associazione a CNA Catania al 50% per tutto il 1° anno</strong>. I marchi mostrati derivano esclusivamente da evidenze reali (nome/sito aziendale).
            </p>
        </div>

        <div class="cols-2">
            <div>
                <div class="section-title">1. Ripartizione Macro-Aree Provinciali</div>
                <table class="table-summary">
                    <thead>
                        <tr>
                            <th>Comprensorio Geografico</th>
                            <th style="text-align: right;">Imprese</th>
                            <th style="text-align: right;">Quota %</th>
                        </tr>
                    </thead>
                    <tbody>
                        {area_rows}
                    </tbody>
                </table>
            </div>

            <div>
                <div class="section-title">2. Marchi Reali Verificati (Zero Inventati)</div>
                <table class="table-summary">
                    <thead>
                        <tr>
                            <th>Marchio Rilevato (Nome / Sito Reale)</th>
                            <th style="text-align: right;">Ditte</th>
                            <th style="text-align: right;">Quota</th>
                        </tr>
                    </thead>
                    <tbody>
                        {marchi_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section-title">3. I 10 Comuni a Più Alta Concentrazione Impiantistica</div>
        <table class="table-summary" style="margin-bottom: 12px;">
            <thead>
                <tr>
                    {"".join(f'<th style="text-align: center;">{_esc(c)}</th>' for c in top_comuni.keys())}
                </tr>
            </thead>
            <tbody>
                <tr>
                    {"".join(f'<td style="text-align: center; font-size: 8.2pt; font-weight: 800; color: #005A9E;">{v} ditte</td>' for v in top_comuni.values())}
                </tr>
            </tbody>
        </table>

        <div style="background: #FFF5F5; border: 1.5px solid #FEB2B2; border-radius: 6px; padding: 8px 12px; font-size: 7.4pt; color: #9B2C2C;">
            <strong>📋 Regola Operativa Human-in-the-Loop (AGENTS.md):</strong><br>
            Contattare prioritariamente le aziende chiamabili ordinate per <strong>Tier A 🔥 VIP</strong> e <strong>Tier B</strong>. Nessuna email o WhatsApp automatizzato senza revisione umana e clausola opt-out.
        </div>
    </div>

    <div class="section-title" style="margin-top: 8px; margin-bottom: 6px;">
        4. Catalogo Integrale Termoidraulica Catania & Provincia ({totale} Imprese Pulite)
    </div>
    <div style="font-size: 7.3pt; color: #718096; margin-bottom: 6px;">
        Ordinamento: prima le {chiamabili} aziende chiamabili (E.164) per ICP Score decrescente, poi le {da_arricchire} aziende da arricchire.
    </div>

    <table class="table-leads">
        <thead>
            <tr>
                <th style="width: 4%; text-align: center;">#</th>
                <th style="width: 24%;">Ragione Sociale & Marchi</th>
                <th style="width: 14%;">Comune & Area</th>
                <th style="width: 15%;">Telefono E.164 & P.IVA</th>
                <th style="width: 13%;">Stato CNA & Tier</th>
                <th style="width: 30%;">Icebreaker 1-to-1 Verificato</th>
            </tr>
        </thead>
        <tbody>
            {"".join(lead_rows_html)}
        </tbody>
    </table>

</body>
</html>"""
    return html


async def generate_termoidraulica_pdf() -> Path:
    csv_file = OUTPUT_TERMOIDRAULICA_CSV if OUTPUT_TERMOIDRAULICA_CSV.exists() else OUTPUT_OUTBOUND_CSV
    print(f"Lettura dataset Termoidraulica da: {csv_file}")
    df = pd.read_csv(csv_file, dtype=str).fillna("")

    print(f"Compilazione Report Integrale per {len(df)} aziende Termoidraulica...")
    html_content = build_termoidraulica_html(df)

    html_file = DATA_DIR / "temp_termoidraulica_report_full.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Compilazione PDF Integrale Termoidraulica con Playwright Chromium...")
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

    print(f"Report PDF Integrale generato con successo: {PDF_OUTPUT_PATH}")
    return PDF_OUTPUT_PATH


if __name__ == "__main__":
    asyncio.run(generate_termoidraulica_pdf())
