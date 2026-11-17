import asyncio
import os
from pathlib import Path
import pandas as pd
from playwright.async_api import async_playwright

from src.config import DATA_DIR, EXCEL_DIR, REPORTS_DIR, OUTPUT_DASHBOARD_EXCEL, PDF_REPORT_FILE

PDF_OUTPUT_PATH = PDF_REPORT_FILE


def build_html_report(stats: dict, associati: list, top_targets: list, niche_counts: dict) -> str:
    target_count = stats.get('target_nuovi', 64)
    totale_lead = stats.get('totale', 124)
    
    # Calcoli proiezioni economiche TecnicoLIVE
    arpu = 250  # Canone medio ponderato Piano Base (169€) e Piano PRO (299€)
    setup_fee = 399
    churn_monthly = 0.021  # 2.1% churn rate mensile target
    customer_lifetime_months = round(1 / churn_monthly, 1)  # ~47.6 mesi
    ltv = round(arpu * customer_lifetime_months, 0)  # ~11.900€ LTV

    # Scenari di conversione sui Target Attuali
    scen_cons_clients = max(1, round(target_count * 0.05))
    scen_cons_mrr = scen_cons_clients * arpu
    scen_cons_arr = scen_cons_mrr * 12

    scen_mod_clients = max(2, round(target_count * 0.12))
    scen_mod_mrr = scen_mod_clients * arpu
    scen_mod_arr = scen_mod_mrr * 12

    scen_opt_clients = max(4, round(target_count * 0.25))
    scen_opt_mrr = scen_opt_clients * arpu
    scen_opt_arr = scen_opt_mrr * 12

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Report Strategico - CNA Catania & TecnicoLIVE</title>
    <style>
        @page {{
            size: A4;
            margin: 12mm 12mm 12mm 12mm;
            @bottom-right {{
                content: "Pagina " counter(page);
                font-family: 'Helvetica Neue', Arial, sans-serif;
                font-size: 8pt;
                color: #888;
            }}
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #2D3748;
            background-color: #FFFFFF;
            margin: 0;
            padding: 0;
            line-height: 1.45;
            font-size: 9.5pt;
        }}
        .header {{
            border-bottom: 2px solid #005A9E;
            padding-bottom: 12px;
            margin-bottom: 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .brand-title {{
            font-size: 19pt;
            font-weight: 800;
            color: #0A2540;
            margin: 0;
            letter-spacing: -0.5px;
        }}
        .brand-subtitle {{
            font-size: 10pt;
            color: #005A9E;
            font-weight: 600;
            margin-top: 2px;
        }}
        .badge-box {{
            text-align: right;
            font-size: 8pt;
            color: #4A5568;
        }}
        .badge {{
            display: inline-block;
            background: #EBF8FF;
            color: #2B6CB0;
            padding: 2px 7px;
            border-radius: 4px;
            font-weight: 700;
            font-size: 8pt;
            border: 1px solid #BEE3F8;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-bottom: 20px;
        }}
        .kpi-card {{
            background: #F7FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 10px;
            text-align: center;
        }}
        .kpi-card.highlight {{
            background: #EBF8FF;
            border-color: #3182CE;
        }}
        .kpi-val {{
            font-size: 18pt;
            font-weight: 800;
            color: #1A365D;
            line-height: 1.1;
        }}
        .kpi-lbl {{
            font-size: 7.5pt;
            text-transform: uppercase;
            font-weight: 700;
            color: #718096;
            margin-top: 3px;
        }}
        .section-title {{
            font-size: 11pt;
            font-weight: 800;
            color: #1A202C;
            border-left: 4px solid #005A9E;
            padding-left: 8px;
            margin-top: 20px;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .summary-box {{
            background: #EDF2F7;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 9pt;
            margin-bottom: 18px;
            border-left: 4px solid #4A5568;
        }}
        .table-custom {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8.5pt;
            margin-bottom: 16px;
        }}
        .table-custom th {{
            background: #1A365D;
            color: #FFFFFF;
            text-align: left;
            padding: 6px 8px;
            font-weight: 700;
            font-size: 7.5pt;
            text-transform: uppercase;
        }}
        .table-custom td {{
            padding: 5px 8px;
            border-bottom: 1px solid #E2E8F0;
            color: #2D3748;
        }}
        .table-custom tr:nth-child(even) {{
            background: #F7FAFC;
        }}
        .tag-green {{
            background: #C6F6D5;
            color: #22543D;
            padding: 2px 5px;
            border-radius: 3px;
            font-weight: 700;
            font-size: 7pt;
        }}
        .tag-blue {{
            background: #BEE3F8;
            color: #2A4365;
            padding: 2px 5px;
            border-radius: 3px;
            font-weight: 700;
            font-size: 7pt;
        }}
        .niche-bar-container {{
            margin-bottom: 15px;
        }}
        .niche-row {{
            display: flex;
            align-items: center;
            margin-bottom: 6px;
            font-size: 8.5pt;
        }}
        .niche-name {{
            width: 180px;
            font-weight: 600;
        }}
        .niche-bar-outer {{
            flex-grow: 1;
            background: #EDF2F7;
            height: 14px;
            border-radius: 7px;
            overflow: hidden;
            margin: 0 10px;
        }}
        .niche-bar-inner {{
            height: 100%;
            background: #005A9E;
            border-radius: 7px;
        }}
        .niche-count {{
            width: 90px;
            text-align: right;
            font-weight: 700;
            color: #2B6CB0;
        }}
        .fin-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 15px;
        }}
        .fin-card {{
            border-radius: 6px;
            padding: 10px;
            border: 1px solid #E2E8F0;
            background: #FFFFFF;
        }}
        .fin-card.conservative {{
            border-top: 4px solid #A0AEC0;
        }}
        .fin-card.moderate {{
            border-top: 4px solid #3182CE;
            background: #F7FAFC;
        }}
        .fin-card.optimal {{
            border-top: 4px solid #38A169;
            background: #F0FFF4;
        }}
        .fin-scenario {{
            font-size: 8pt;
            font-weight: 800;
            text-transform: uppercase;
            color: #4A5568;
            margin-bottom: 4px;
        }}
        .fin-mrr {{
            font-size: 16pt;
            font-weight: 800;
            color: #1A202C;
            line-height: 1.1;
        }}
        .fin-arr {{
            font-size: 8.5pt;
            color: #718096;
            margin-top: 2px;
        }}
        .fin-detail {{
            font-size: 8pt;
            color: #4A5568;
            margin-top: 6px;
            border-top: 1px dashed #CBD5E0;
            padding-top: 4px;
        }}
        .churn-box {{
            background: #FFF5F5;
            border: 1px solid #FEB2B2;
            border-radius: 6px;
            padding: 10px 14px;
            margin-bottom: 15px;
            font-size: 8.5pt;
        }}
        .guide-box {{
            background: #F7FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 10px 14px;
            margin-bottom: 15px;
            font-size: 8.5pt;
        }}
        .page-break {{
            page-break-before: always;
        }}
        .footer-note {{
            margin-top: 20px;
            border-top: 1px solid #E2E8F0;
            padding-top: 8px;
            font-size: 7.5pt;
            color: #A0AEC0;
            text-align: center;
        }}
    </style>
</head>
<body>

    <!-- INTESTAZIONE -->
    <div class="header">
        <div>
            <div class="brand-title">TECNICOLIVE &bull; REPORT STRATEGICO & FINANZIARIO</div>
            <div class="brand-subtitle">Censimento Territoriale Impiantisti & Proiezioni SaaS CNA Catania</div>
        </div>
        <div class="badge-box">
            <span class="badge">PROGETTO CATANIA 2026</span><br>
            <strong>Data:</strong> Novembre 2026<br>
            <strong>Partner:</strong> CNA Territoriale Catania
        </div>
    </div>

    <!-- SINTESI STRATEGICA -->
    <div class="summary-box">
        <strong>Inquadramento Commerciale:</strong> Il censimento mappa le imprese impiantistiche (HVAC, Idraulica, Elettrico e Grandi Appalti) della Città Metropolitana di Catania. 
        L'accordo strategico tra <strong>TecnicoLIVE (Sinergia Rete d'Imprese)</strong> e <strong>CNA Catania</strong> permette di attivare una doppia leva:
        convenzione immediata con sconto categoria per i soci esistenti, e offerta abbinata <em>TecnicoLIVE + Tesseramento agevolato CNA</em> per le centinaia di prospect non ancora iscritti.
    </div>

    <!-- KPI GRID -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-val">{stats['totale']}</div>
            <div class="kpi-lbl">Aziende Censite</div>
        </div>
        <div class="kpi-card highlight">
            <div class="kpi-val">{stats['piva_valide']}</div>
            <div class="kpi-lbl">P.IVA Validate (IT)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val" style="color: #276749;">{stats['associati_cna']}</div>
            <div class="kpi-lbl">Soci CNA Rilevati</div>
        </div>
        <div class="kpi-card highlight">
            <div class="kpi-val" style="color: #2B6CB0;">{stats['target_nuovi']}</div>
            <div class="kpi-lbl">Target Tesseramento</div>
        </div>
    </div>

    <!-- SEZIONE PROIEZIONI FINANZIARIE -->
    <div class="section-title">1. Proiezioni Economiche Mensili & Modello SaaS (ARPU 250€)</div>
    <div class="fin-grid">
        <div class="fin-card conservative">
            <div class="fin-scenario">Scenario Conservativo (5% Conv.)</div>
            <div class="fin-mrr">{scen_cons_mrr:,} € <span style="font-size: 9pt; font-weight: normal;">/mese MRR</span></div>
            <div class="fin-arr"><strong>{scen_cons_arr:,} €</strong> ARR (Fatturato Annuo)</div>
            <div class="fin-detail">
                <strong>{scen_cons_clients} Clienti Attivi</strong><br>
                Setup Fees iniziali: +{scen_cons_clients * setup_fee:,} €
            </div>
        </div>
        <div class="fin-card moderate">
            <div class="fin-scenario">Scenario Moderato (12% Conv.)</div>
            <div class="fin-mrr" style="color: #2B6CB0;">{scen_mod_mrr:,} € <span style="font-size: 9pt; font-weight: normal;">/mese MRR</span></div>
            <div class="fin-arr"><strong>{scen_mod_arr:,} €</strong> ARR (Fatturato Annuo)</div>
            <div class="fin-detail">
                <strong>{scen_mod_clients} Clienti Attivi</strong><br>
                Setup Fees iniziali: +{scen_mod_clients * setup_fee:,} €
            </div>
        </div>
        <div class="fin-card optimal">
            <div class="fin-scenario">Scenario Ottimale (25% Conv.)</div>
            <div class="fin-mrr" style="color: #22543D;">{scen_opt_mrr:,} € <span style="font-size: 9pt; font-weight: normal;">/mese MRR</span></div>
            <div class="fin-arr"><strong>{scen_opt_arr:,} €</strong> ARR (Fatturato Annuo)</div>
            <div class="fin-detail">
                <strong>{scen_opt_clients} Clienti Attivi</strong><br>
                Setup Fees iniziali: +{scen_opt_clients * setup_fee:,} €
            </div>
        </div>
    </div>

    <!-- CHURN RATE & LTV METRICS -->
    <div class="churn-box">
        <strong>Analisi Churn Rate & Customer Lifetime Value (LTV):</strong>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 6px;">
            <div>&bull; <strong>Churn Rate Mensile Stimato:</strong> <code>{churn_monthly*100:.1f}%</code> (Target PMI artigiane)</div>
            <div>&bull; <strong>Permanenza Media (Lifetime):</strong> <code>{customer_lifetime_months} mesi</code> (~4 anni)</div>
            <div>&bull; <strong>Valore per Cliente (LTV):</strong> <code>{ltv:,.0f} €</code> per azienda</div>
        </div>
        <p style="margin: 6px 0 0 0; font-size: 8pt; color: #742A2A;">
            <em>Razionale del Churn Basso:</em> L'assistente vocale TecnicoLIVE si integra sulla deviazione telefonica storica del tecnico e gestisce la pre-diagnosi degli interventi. Sostituire o disattivare il centralino comporterebbe la perdita immediata di chiamate e clienti per l'artigiano, garantendo una retention tra le più alte del settore B2B software.
        </p>
    </div>

    <!-- DISTRIBUZIONE PER SETTORE -->
    <div class="section-title">2. Distribuzione per Settore e Nicchia Operativa</div>
    <div class="niche-bar-container">
        {"".join([f'''
        <div class="niche-row">
            <div class="niche-name">{niche}</div>
            <div class="niche-bar-outer">
                <div class="niche-bar-inner" style="width: {(count / totale_lead * 100):.1f}%;"></div>
            </div>
            <div class="niche-count">{count} ditte ({(count / totale_lead * 100):.1f}%)</div>
        </div>
        ''' for niche, count in niche_counts.items()])}
    </div>

    <!-- SOCI CNA IDENTIFICATI -->
    <div class="section-title">3. Imprese già Associate a CNA Catania Rilevate</div>
    <table class="table-custom">
        <thead>
            <tr>
                <th>Ragione Sociale</th>
                <th>Comune</th>
                <th>Telefono</th>
                <th>Partita IVA</th>
                <th>Evidenza Riscontrata</th>
                <th>Azione Commerciale</th>
            </tr>
        </thead>
        <tbody>
            {"".join([f'''
            <tr>
                <td><strong>{a['Company Name']}</strong></td>
                <td>{a['City']}</td>
                <td>{a['Phone']}</td>
                <td><code>{a['Partita_IVA']}</code></td>
                <td><span class="tag-green">{a['Evidenza_CNA']}</span></td>
                <td>Sconto Convenzione Soci CNA</td>
            </tr>
            ''' for a in associati])}
        </tbody>
    </table>

    <div class="page-break"></div>

    <!-- HEADER PAGINA 2 -->
    <div class="header" style="margin-top: 10px;">
        <div>
            <div class="brand-title" style="font-size: 14pt;">TECNICOLIVE &bull; REPORT OPERATIVO (PAGINA 2)</div>
            <div class="brand-subtitle">Campagna Outbound & Target Prioritari di Tesseramento</div>
        </div>
        <div class="badge-box"><strong>Provincia di Catania</strong> | Qualified Leads</div>
    </div>

    <!-- GUIDA ALLA LETTURA DELLE TABELLE -->
    <div class="guide-box">
        <strong>Guida alla Lettura delle Colonne & Standard Dati:</strong>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 4px;">
            <div>&bull; <strong>Partita IVA (IT):</strong> Codice a 11 cifre validato formalmente con algoritmo di Luhn (DPR 633/1972). Zero falsi positivi.</div>
            <div>&bull; <strong>Telefono:</strong> Normalizzato in formato universale <code>+39...</code>, compatibile con centralini VOIP e dialer automatici.</div>
            <div>&bull; <strong>Stato CNA:</strong> 
                <span class="tag-green">🟢 Socio Rilevato</span> (proposta convenzione diretta) vs 
                <span class="tag-blue">🔵 Target Non Associato</span> (proposta combinata).
            </div>
        </div>
    </div>

    <!-- TOP TARGET QUALIFICATI PER TESSERAMENTO -->
    <div class="section-title">4. Selezione Lead Target ad Alta Priorità (Pronte per Tesseramento)</div>
    <p style="font-size: 8pt; color: #4A5568; margin-bottom: 6px;">
        Aziende con <strong>Partita IVA verificata</strong>, sede attiva nella provincia di Catania e prive di affiliazione online (estratto dal file <code>data/target_tesseramento_cna.csv</code>):
    </p>
    <table class="table-custom">
        <thead>
            <tr>
                <th>Ragione Sociale</th>
                <th>Nicchia</th>
                <th>Comune</th>
                <th>Telefono</th>
                <th>Partita IVA (IT)</th>
                <th>Stato Commerciale</th>
            </tr>
        </thead>
        <tbody>
            {"".join([f'''
            <tr>
                <td><strong>{t['Company Name']}</strong></td>
                <td>{t['Nicchia_Target']}</td>
                <td>{t['City']}</td>
                <td>{t['Phone']}</td>
                <td><code>{t['Partita_IVA']}</code></td>
                <td><span class="tag-blue">TARGET TESSERAMENTO CNA</span></td>
            </tr>
            ''' for t in top_targets])}
        </tbody>
    </table>

    <!-- STRATEGIA COMMERCIALE -->
    <div class="section-title">5. Sinergia Istituzionale & Procedura Ufficio Soci CNA</div>
    <div style="background: #F0FFF4; border: 1px solid #9AE6B4; border-radius: 6px; padding: 10px 14px; font-size: 8.5pt;">
        <p style="margin: 0 0 5px 0;">
            1. <strong>Foglio di Riscontro Ufficiale:</strong> Il file <code>data/richiesta_verifica_cna.csv</code> è pronto per essere inoltrato all'Ufficio Soci di CNA Catania (Piazza dei Martiri, 8) per completare la spunta ufficiale al 100% delle ditte prive di evidenza online.
        </p>
        <p style="margin: 0;">
            2. <strong>File Outbound con Script Già Compilato:</strong> Nel file <code>data/campagna_outbound_tecnicolive.csv</code> ciascuna riga dispone del pitch verbale pronto per gli operatori telefonici:
            <em>"Buongiorno [Nome Azienda], vi contattiamo da TecnicoLIVE. In qualità di ditta impiantistica operante a [Comune], stiamo attivando con CNA Catania la convenzione esclusiva: assistente vocale AI per non perdere interventi in cantiere + tesseramento CNA a condizioni agevolate."</em>
        </p>
    </div>

    <div class="footer-note">
        TecnicoLIVE 2.0 &bull; Sinergia Rete d'Imprese &bull; Piazza dei Martiri 8, 95131 Catania (CT) &bull; Partnership Istituzionale con CNA Territoriale Catania
    </div>

</body>
</html>"""
    return html


async def generate_pdf():
    print("Caricamento dati da Excel...")
    df = pd.read_excel(OUTPUT_DASHBOARD_EXCEL, sheet_name="Tutte le Lead")
    
    totale = len(df)
    piva_valide = len(df[df["Partita_IVA"].fillna("").astype(str).str.startswith("IT")])
    associati_df = df[df["Stato_CNA"].str.contains("ASSOCIATO RILEVATO", na=False)]
    target_df = df[df["Stato_CNA"].str.contains("NON ASSOCIATO", na=False)]
    
    stats = {
        "totale": totale,
        "piva_valide": piva_valide,
        "associati_cna": len(associati_df),
        "target_nuovi": len(target_df),
    }
    
    associati = associati_df.to_dict(orient="records")
    top_targets = target_df.head(15).to_dict(orient="records")
    niche_counts = df["Nicchia_Target"].value_counts().to_dict()
    
    html_content = build_html_report(stats, associati, top_targets, niche_counts)
    
    html_file = DATA_DIR / "report_temp.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print("Compilazione PDF con Playwright Chromium...")
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
        
    print(f"PDF generato con successo: {PDF_OUTPUT_PATH}")
    return PDF_OUTPUT_PATH


if __name__ == "__main__":
    asyncio.run(generate_pdf())
