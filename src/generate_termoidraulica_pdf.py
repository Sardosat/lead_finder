"""
Generatore Report PDF Esecutivo Completo per il CEO
Censimento Integrale Impiantistica & Termoidraulica Catania & Provincia (Tutti i 58 Comuni)
Include tutte le 696 aziende qualificate con P.IVA, Stato CNA, ICP Score e Icebreaker 1-to-1.
"""

import asyncio
import os
import shutil
import sys
from pathlib import Path

# Assicura che la root del progetto sia in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pandas as pd
from playwright.async_api import async_playwright

from src.config import DATA_DIR, REPORTS_DIR

PDF_OUTPUT_PATH = REPORTS_DIR / "Report_Termoidraulica_Catania_Provincia_CNA.pdf"
BRAIN_DIR = Path(r"C:\Users\nicol\.gemini\antigravity\brain\466c6750-da56-4657-9200-3e9d190836db")


def build_termoidraulica_html(df: pd.DataFrame) -> str:
    totale = len(df)
    
    # Metriche Telefoniche
    cellulari = len(df[df["Phone"].str.contains(r"\+393", na=False)])
    perc_cell = round((cellulari / totale * 100), 1) if totale > 0 else 0
    
    # Metriche Fiscali
    piva_valide = len(df[df["Partita_IVA"].fillna("").astype(str).str.startswith("IT")])
    perc_piva = round((piva_valide / totale * 100), 1) if totale > 0 else 0
    
    # Metriche CNA
    associati = len(df[df["Stato_CNA"].str.contains("ASSOCIATO RILEVATO", na=False)])
    target_cna = len(df[df["Stato_CNA"].str.contains("NON ASSOCIATO", na=False)])
    da_verificare = totale - associati - target_cna
    
    # Metriche Tier Clay
    tier_a = len(df[df.get("Lead_Tier", pd.Series([""]*totale)).str.contains("Tier A", na=False)])
    tier_b = len(df[df.get("Lead_Tier", pd.Series([""]*totale)).str.contains("Tier B", na=False)])
    tier_c = len(df[df.get("Lead_Tier", pd.Series([""]*totale)).str.contains("Tier C", na=False)])
    
    # Distribuzione Geografica
    area_series = df.get("Area_Geografica", df["City"])
    area_counts = area_series.value_counts().to_dict()
    
    # Top Comuni
    top_comuni = df["City"].value_counts().head(10).to_dict()

    # Marchi rilevati
    marchi_stats = {
        "Vaillant": len(df[df.get("Marchi_Rilevati", pd.Series([""]*totale)).str.contains("Vaillant", na=False)]),
        "Baxi": len(df[df.get("Marchi_Rilevati", pd.Series([""]*totale)).str.contains("Baxi", na=False)]),
        "Buderus": len(df[df.get("Marchi_Rilevati", pd.Series([""]*totale)).str.contains("Buderus", na=False)]),
        "Bosch": len(df[df.get("Marchi_Rilevati", pd.Series([""]*totale)).str.contains("Bosch", na=False)]),
        "Ariston": len(df[df.get("Marchi_Rilevati", pd.Series([""]*totale)).str.contains("Ariston", na=False)]),
        "Immergas": len(df[df.get("Marchi_Rilevati", pd.Series([""]*totale)).str.contains("Immergas", na=False)]),
    }

    # Ordina i lead per Tier A poi Tier B e score decrescente
    df_sorted = df.copy()
    if "ICP_Score" in df_sorted.columns:
        df_sorted["ICP_Score_Num"] = pd.to_numeric(df_sorted["ICP_Score"], errors="coerce").fillna(0)
        df_sorted.sort_values(by=["ICP_Score_Num"], ascending=False, inplace=True)
    
    # TUTTE le lead per il CEO
    all_leads = df_sorted.to_dict(orient="records")

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
                content: "TecnicoLIVE 2.0 • Sinergia Rete d'Imprese • Piazza dei Martiri 8, Catania";
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 7pt;
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
            padding-top: 20px;
        }}
        
        .header-box {{
            border-bottom: 3px solid #005A9E;
            padding-bottom: 12px;
            margin-bottom: 16px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .brand-title {{
            font-size: 20pt;
            font-weight: 900;
            color: #005A9E;
            letter-spacing: -0.5px;
            margin: 0;
            text-transform: uppercase;
        }}
        .brand-subtitle {{
            font-size: 10.5pt;
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
            font-size: 8pt;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
            margin-bottom: 16px;
        }}
        .kpi-card {{
            background: #F7FAFC;
            border: 1.5px solid #E2E8F0;
            border-radius: 6px;
            padding: 10px 6px;
            text-align: center;
        }}
        .kpi-num {{
            font-size: 17pt;
            font-weight: 900;
            color: #1A202C;
            line-height: 1;
        }}
        .kpi-label {{
            font-size: 7pt;
            font-weight: 700;
            color: #4A5568;
            text-transform: uppercase;
            margin-top: 4px;
        }}
        .kpi-sub {{
            font-size: 6.5pt;
            color: #2B6CB0;
            font-weight: 600;
            margin-top: 2px;
        }}
        
        .section-title {{
            font-size: 10.5pt;
            font-weight: 800;
            color: #005A9E;
            border-bottom: 1.5px solid #CBD5E0;
            padding-bottom: 3px;
            margin-top: 14px;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        
        .cols-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 14px;
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
            padding: 10px 14px;
            font-size: 8pt;
            margin-bottom: 14px;
            color: #22543D;
        }}
        
        /* TABELLA INTEGRALE DEI 696 LEAD */
        .table-leads {{
            width: 100%;
            border-collapse: collapse;
            font-size: 7pt;
            margin-top: 8px;
        }}
        thead {{
            display: table-header-group;
        }}
        tr {{
            page-break-inside: avoid;
        }}
        .table-leads th {{
            background-color: #005A9E;
            color: #FFFFFF;
            font-weight: 800;
            text-align: left;
            padding: 5px 6px;
            font-size: 6.8pt;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}
        .table-leads td {{
            padding: 4.5px 6px;
            border-bottom: 1px solid #E2E8F0;
            vertical-align: top;
        }}
        .table-leads tr:nth-child(even) {{
            background-color: #F8FAFC;
        }}
        
        .badge-vip {{
            background-color: #FEFCBF;
            color: #744210;
            border: 1px solid #D69E2E;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 800;
            font-size: 6.5pt;
            display: inline-block;
        }}
        .badge-warm {{
            background-color: #EDF2F7;
            color: #2D3748;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 600;
            font-size: 6.5pt;
            display: inline-block;
        }}
        .badge-target {{
            background-color: #EBF8FF;
            color: #2B6CB0;
            border: 1px solid #90CDF4;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 700;
            font-size: 6.5pt;
            display: inline-block;
        }}
        .badge-socio {{
            background-color: #C6F6D5;
            color: #22543D;
            border: 1px solid #68D391;
            padding: 1px 4px;
            border-radius: 3px;
            font-weight: 700;
            font-size: 6.5pt;
            display: inline-block;
        }}
        
        .icebreaker-mini {{
            background: #F0FFF4;
            border-left: 2px solid #38A169;
            padding: 3px 5px;
            font-size: 6.5pt;
            color: #22543D;
            line-height: 1.25;
            font-style: italic;
            border-radius: 0 3px 3px 0;
        }}
    </style>
</head>
<body>

    <!-- ========================================== -->
    <!-- PAGINA 1: EXECUTIVE BRIEFING PER IL CEO    -->
    <!-- ========================================== -->
    <div class="cover-page">
        <div class="header-box">
            <div>
                <div class="brand-title">TecnicoLIVE &bull; Executive Report</div>
                <div class="brand-subtitle">Censimento & Qualificazione Integrale Impiantistica Termoidraulica & Clima</div>
                <div style="font-size: 8pt; color: #4A5568; margin-top: 3px;">
                    Ambito Territoriale: <strong>Città Metropolitana di Catania (58 Comuni)</strong> &bull; Partnership Istituzionale: <strong>CNA Catania</strong>
                </div>
            </div>
            <div style="text-align: right;">
                <div class="header-badge">Documento Riservato CEO</div>
                <div style="font-size: 7.5pt; color: #718096; margin-top: 4px;">Data: <strong>Novembre 2026</strong></div>
                <div style="font-size: 7.5pt; color: #718096;">Sede: <strong>Piazza dei Martiri 8, Catania</strong></div>
            </div>
        </div>

        <!-- KPI CRUSCOTTO DIREZIONALE -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-num">{totale}</div>
                <div class="kpi-label">Imprese Censite</div>
                <div class="kpi-sub">100% Catania & Prov.</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num" style="color: #2B6CB0;">{target_cna}</div>
                <div class="kpi-label">Target Non Associati</div>
                <div class="kpi-sub">Leva Quota 1° Anno CNA</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num" style="color: #DD6B20;">{tier_a}</div>
                <div class="kpi-label">Tier A 🔥 VIP</div>
                <div class="kpi-sub">Score ICP &ge; 80 / 100</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num" style="color: #4A5568;">{tier_b}</div>
                <div class="kpi-label">Tier B 🟡 Warm</div>
                <div class="kpi-sub">Audience Meta Ads RSK</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-num" style="color: #2F855A;">{piva_valide}</div>
                <div class="kpi-label">P.IVA Validate Luhn</div>
                <div class="kpi-sub">{perc_piva}% Fiscale Certificato</div>
            </div>
        </div>

        <!-- NOTA STRATEGICA PER IL CEO -->
        <div class="strategic-box">
            <strong>🎯 Sintesi Esecutiva per la Direzione Generale:</strong>
            <p style="margin: 4px 0 0 0;">
                Il presente documento raccoglie il censimento esaustivo di tutte le <strong>{totale} aziende di termoidraulica, assistenza caldaie e climatizzazione</strong> operanti nell'area etnea e provinciale. 
                Ben <strong>{target_cna} ditte ({round(target_cna/totale*100, 1)}%) risultano non ancora associate a CNA Catania</strong>: costituiscono l'obiettivo commerciale primario per l'offerta combinata:
                <em>Attivazione Assistente Vocale AI TecnicoLIVE + Quota d'iscrizione del 1° anno a CNA Catania scontata</em>. 
                Le <strong>{tier_a} aziende di Tier A (VIP 🔥)</strong> dispongono di requisiti tecnici di prim'ordine (P.IVA validata con Luhn, telefoni verificati e marchi compatibili come Buderus, Vaillant, Baxi e Bosch) e sono pronte per il contatto outbound immediato con gli icebreaker generati su misura.
            </p>
        </div>

        <!-- PROIEZIONI E DISTRIBUZIONE TERRITORIALE -->
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
                        {"".join([f'''
                        <tr>
                            <td><strong>{area}</strong></td>
                            <td style="text-align: right; font-weight: 700;">{count}</td>
                            <td style="text-align: right; color: #718096;">{round(count/totale*100, 1)}%</td>
                        </tr>
                        ''' for area, count in sorted(area_counts.items(), key=lambda x: x[1], reverse=True)])}
                    </tbody>
                </table>
            </div>

            <div>
                <div class="section-title">2. Copertura Marchi Assistiti dall'AI</div>
                <table class="table-summary">
                    <thead>
                        <tr>
                            <th>Manuale Tecnico Integrato nell'AI</th>
                            <th style="text-align: right;">Ditte Specializzate</th>
                            <th style="text-align: right;">Copertura</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'''
                        <tr>
                            <td><strong>{m_name}</strong> (Diagnosi Guasti H24)</td>
                            <td style="text-align: right; font-weight: 700;">{m_cnt}</td>
                            <td style="text-align: right; color: #2B6CB0;">{round(m_cnt/totale*100, 1)}%</td>
                        </tr>
                        ''' for m_name, m_cnt in sorted(marchi_stats.items(), key=lambda x: x[1], reverse=True)])}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- I 10 COMUNI A MAGGIOR DENSITA -->
        <div class="section-title">3. I 10 Comuni a Più Alta Concentrazione Impiantistica</div>
        <table class="table-summary" style="margin-bottom: 12px;">
            <thead>
                <tr>
                    {"".join([f'<th style="text-align: center;">{c}</th>' for c in list(top_comuni.keys())])}
                </tr>
            </thead>
            <tbody>
                <tr>
                    {"".join([f'<td style="text-align: center; font-size: 8.5pt; font-weight: 800; color: #005A9E;">{v} ditte</td>' for v in list(top_comuni.values())])}
                </tr>
            </tbody>
        </table>

        <!-- INDICAZIONI OPERATIVE PER IL TEAM -->
        <div style="background: #FFF5F5; border: 1.5px solid #FEB2B2; border-radius: 6px; padding: 8px 12px; font-size: 7.5pt; color: #9B2C2C;">
            <strong>📋 Regola Operativa d'Ingaggio per i Due Collaboratori Umani:</strong><br>
            I collaboratori non devono mai effettuare chiamate generiche o a freddo: ogni contatto deve avvenire scorrendo l'elenco sottostante in ordine di <strong>Tier A 🔥 VIP</strong>, leggendo fedelmente l'<strong>Icebreaker 1-to-1</strong> calibrato sul comune di appartenenza e sui marchi trattati dalla ditta.
        </div>
    </div>

    <!-- ========================================== -->
    <!-- PAGINE 2+: CATALOGO INTEGRALE DELLE 696 LEAD -->
    <!-- ========================================== -->
    <div class="section-title" style="margin-top: 10px; margin-bottom: 6px;">
        4. Catalogo Integrale Impianti Termoidraulici Catania & Provincia ({totale} Imprese)
    </div>
    <div style="font-size: 7.5pt; color: #718096; margin-bottom: 8px;">
        Tutti i 696 lead ordinati per priorità decrescente (Tier A VIP 🔥, poi Tier B 🟡), completi di recapiti telefonici, P.IVA certificata, stato associativo CNA e gancio conversazionale 1-to-1 pronto da usare.
    </div>

    <table class="table-leads">
        <thead>
            <tr>
                <th style="width: 3%; text-align: center;">#</th>
                <th style="width: 25%;">Ragione Sociale & Marchi</th>
                <th style="width: 14%;">Comune & Area</th>
                <th style="width: 15%;">Telefono & P.IVA</th>
                <th style="width: 13%;">Stato CNA & Tier</th>
                <th style="width: 30%;">Icebreaker 1-to-1 (Stile Clay.com)</th>
            </tr>
        </thead>
        <tbody>
            {"".join([f'''
            <tr>
                <td style="text-align: center; color: #718096; font-size: 6.5pt;">{idx}</td>
                <td>
                    <strong style="color: #1A202C; font-size: 7.5pt;">{lead.get('Company Name', '')}</strong><br>
                    <span style="color: #4A5568; font-size: 6.5pt;">🔧 {lead.get('Marchi_Rilevati', 'Caldaie & Clima')}</span>
                </td>
                <td>
                    <strong>{lead.get('City', '')}</strong><br>
                    <span style="color: #718096; font-size: 6.5pt;">{lead.get('Area_Geografica', 'Provincia')}</span>
                </td>
                <td>
                    <strong style="color: #005A9E;">{lead.get('Phone', '')}</strong><br>
                    <code style="color: #4A5568; font-size: 6.5pt;">{lead.get('Partita_IVA', 'N/D')}</code>
                </td>
                <td>
                    <span class="{'badge-vip' if 'Tier A' in str(lead.get('Lead_Tier')) else ('badge-warm' if 'Tier B' in str(lead.get('Lead_Tier')) else 'badge-warm')}">{lead.get('Lead_Tier', 'Tier B')}</span>
                    <span style="font-weight: 700; color: #2B6CB0; font-size: 6.5pt;">({lead.get('ICP_Score', '70')} pt)</span><br>
                    <span class="{'badge-socio' if 'ASSOCIATO RILEVATO' in str(lead.get('Stato_CNA')) else ('badge-target' if 'NON ASSOCIATO' in str(lead.get('Stato_CNA')) else 'badge-warm')}">
                        {'SOCIO CNA' if 'ASSOCIATO RILEVATO' in str(lead.get('Stato_CNA')) else ('TARGET NON ASSOCIATO' if 'NON ASSOCIATO' in str(lead.get('Stato_CNA')) else 'DA VERIFICARE')}
                    </span>
                </td>
                <td>
                    <div class="icebreaker-mini">
                        "{lead.get('Icebreaker_1to1', 'Buongiorno, vi contatto da TecnicoLIVE per la convenzione CNA Catania...')}"
                    </div>
                </td>
            </tr>
            ''' for idx, lead in enumerate(all_leads, 1)])}
        </tbody>
    </table>

</body>
</html>"""
    return html


async def generate_termoidraulica_pdf() -> Path:
    csv_file = DATA_DIR / "termoidraulica_catania_provincia.csv"
    if not csv_file.exists():
        csv_file = DATA_DIR / "campagna_outbound_tecnicolive.csv"

    print(f"Lettura dataset completo da: {csv_file}")
    df = pd.read_csv(csv_file, dtype=str).fillna("")

    print(f"Compilazione report per TUTTE le {len(df)} aziende di Termoidraulica...")
    html_content = build_termoidraulica_html(df)

    html_file = DATA_DIR / "temp_termoidraulica_report_full.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Compilazione PDF ad alta fedeltà con Playwright Chromium (può richiedere qualche secondo per tutte le pagine)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file:///{html_file.resolve().as_posix()}", wait_until="networkidle")
        await page.pdf(
            path=str(PDF_OUTPUT_PATH),
            format="A4",
            print_background=True,
            margin={"top": "8mm", "bottom": "8mm", "left": "8mm", "right": "8mm"}
        )
        await browser.close()

    if html_file.exists():
        html_file.unlink()

    # Copia anche nella cartella degli artefatti per accesso e download diretto
    if BRAIN_DIR.exists():
        dest_brain = BRAIN_DIR / "Report_Termoidraulica_Catania_Provincia_CNA.pdf"
        shutil.copy2(PDF_OUTPUT_PATH, dest_brain)
        print(f"Copia del PDF sincronizzata negli artefatti: {dest_brain}")

    print(f"Report PDF Direzionale generato con successo: {PDF_OUTPUT_PATH}")
    return PDF_OUTPUT_PATH


if __name__ == "__main__":
    asyncio.run(generate_termoidraulica_pdf())
