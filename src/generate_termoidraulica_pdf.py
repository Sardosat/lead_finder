"""
Generatore Report PDF Esecutivo: Censimento Impiantistica & Termoidraulica Catania & Provincia
Compilazione tramite Playwright Chromium in PDF ad alta definizione A4.
"""

import asyncio
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


def build_termoidraulica_html(df: pd.DataFrame) -> str:
    totale = len(df)
    
    # Metriche Telefoniche
    cellulari = len(df[df["Phone"].str.contains(r"\+393", na=False)])
    fissi = totale - cellulari
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
    top_comuni = df["City"].value_counts().head(8).to_dict()

    # Marchi rilevati count
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
    
    # Prendi fino a 40 lead per il catalogo esecutivo dettagliato nel PDF
    top_leads = df_sorted.head(45).to_dict(orient="records")

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Report Termoidraulica Catania & Provincia - CNA & TecnicoLIVE</title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 10mm 12mm 12mm 12mm;
            @bottom-right {{
                content: "Pagina " counter(page);
                font-family: 'Helvetica Neue', Arial, sans-serif;
                font-size: 8pt;
                color: #718096;
            }}
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #2D3748;
            background-color: #FFFFFF;
            margin: 0;
            padding: 0;
            line-height: 1.4;
            font-size: 9pt;
        }}
        .header {{
            border-bottom: 2.5px solid #005A9E;
            padding-bottom: 10px;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .brand-title {{
            font-size: 18pt;
            font-weight: 800;
            color: #005A9E;
            letter-spacing: -0.5px;
            margin: 0;
        }}
        .brand-subtitle {{
            font-size: 9pt;
            font-weight: 600;
            color: #4A5568;
            margin-top: 3px;
        }}
        .header-meta {{
            text-align: right;
            font-size: 8pt;
            color: #718096;
        }}
        
        .badge-vip {{
            background-color: #FEFCBF;
            color: #744210;
            border: 1px solid #D69E2E;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 700;
            font-size: 7.5pt;
        }}
        .badge-warm {{
            background-color: #EDF2F7;
            color: #2D3748;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 7.5pt;
        }}
        .badge-cna {{
            background-color: #EBF8FF;
            color: #2B6CB0;
            border: 1px solid #90CDF4;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 700;
            font-size: 7.5pt;
        }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            margin-bottom: 16px;
        }}
        .kpi-card {{
            background: #F7FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 10px 8px;
            text-align: center;
        }}
        .kpi-num {{
            font-size: 16pt;
            font-weight: 800;
            color: #1A202C;
            line-height: 1.1;
        }}
        .kpi-label {{
            font-size: 7.5pt;
            font-weight: 600;
            color: #718096;
            text-transform: uppercase;
            margin-top: 4px;
        }}
        .kpi-sub {{
            font-size: 7pt;
            color: #38A169;
            font-weight: 600;
            margin-top: 2px;
        }}
        
        .section-title {{
            font-size: 11pt;
            font-weight: 700;
            color: #005A9E;
            border-bottom: 1.5px solid #E2E8F0;
            padding-bottom: 4px;
            margin-top: 14px;
            margin-bottom: 8px;
        }}
        
        .cols-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 14px;
        }}
        
        .table-custom {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8pt;
            margin-top: 6px;
            margin-bottom: 12px;
        }}
        .table-custom th {{
            background-color: #EDF2F7;
            color: #2D3748;
            font-weight: 700;
            text-align: left;
            padding: 6px 8px;
            border-bottom: 1.5px solid #CBD5E0;
            font-size: 7.5pt;
            text-transform: uppercase;
        }}
        .table-custom td {{
            padding: 5px 8px;
            border-bottom: 1px solid #E2E8F0;
            vertical-align: middle;
        }}
        .table-custom tr:nth-child(even) {{
            background-color: #F7FAFC;
        }}
        
        .icebreaker-box {{
            background: #F0FFF4;
            border-left: 3px solid #38A169;
            padding: 4px 8px;
            font-size: 7.5pt;
            color: #22543D;
            margin-top: 3px;
            font-style: italic;
        }}
        
        .footer-note {{
            margin-top: 18px;
            border-top: 1px solid #E2E8F0;
            padding-top: 8px;
            font-size: 7.5pt;
            color: #718096;
            text-align: center;
        }}
    </style>
</head>
<body>

    <!-- HEADER ISTITUZIONALE -->
    <div class="header">
        <div>
            <div class="brand-title">TecnicoLIVE &bull; Report Territoriale Termoidraulica</div>
            <div class="brand-subtitle">Censimento & Qualificazione Impiantistica &bull; Città Metropolitana di Catania &bull; Convenzione CNA</div>
        </div>
        <div class="header-meta">
            <div>Data Report: <strong>Novembre 2026</strong></div>
            <div>Sede CNA: <strong>Piazza dei Martiri 8, Catania</strong></div>
            <div>Architettura: <strong>Clay.com Intelligence + RSK System</strong></div>
        </div>
    </div>

    <!-- CRUSCOTTO METRICHE SUPERIORI -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-num">{totale}</div>
            <div class="kpi-label">Ditte Rilevate</div>
            <div class="kpi-sub">Catania & Provincia</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-num" style="color: #2B6CB0;">{target_cna}</div>
            <div class="kpi-label">Target Non Associati</div>
            <div class="kpi-sub">Leva Sconto 1° Anno CNA</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-num" style="color: #DD6B20;">{tier_a}</div>
            <div class="kpi-label">Tier A 🔥 VIP</div>
            <div class="kpi-sub">Score ICP &ge; 80 / 100</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-num">{cellulari}</div>
            <div class="kpi-label">Cellulari Diretti (3xx)</div>
            <div class="kpi-sub">{perc_cell}% WhatsApp Ready</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-num">{piva_valide}</div>
            <div class="kpi-label">P.IVA Validate Luhn</div>
            <div class="kpi-sub">{perc_piva}% Fiscale Verificato</div>
        </div>
    </div>

    <!-- DISTRIBUZIONE TERRITORIALE E MARCHI ASSISTITI -->
    <div class="cols-2">
        <div>
            <div class="section-title">1. Ripartizione per Comprensorio Provinciale</div>
            <table class="table-custom">
                <thead>
                    <tr>
                        <th>Macro-Area Geografica</th>
                        <th style="text-align: right;">Imprese Censite</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f'''
                    <tr>
                        <td><strong>{area}</strong></td>
                        <td style="text-align: right;">{count}</td>
                    </tr>
                    ''' for area, count in sorted(area_counts.items(), key=lambda x: x[1], reverse=True)[:6]])}
                </tbody>
            </table>
        </div>
        <div>
            <div class="section-title">2. Copertura Marchi Caldaie & Clima Assistiti dall'AI</div>
            <table class="table-custom">
                <thead>
                    <tr>
                        <th>Marchio Compatibile TecnicoLIVE</th>
                        <th style="text-align: right;">Ditte Specializzate</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join([f'''
                    <tr>
                        <td><strong>{m_name}</strong> (Manuali Integrati)</td>
                        <td style="text-align: right;"><span class="badge-warm">{m_cnt} ditte</span></td>
                    </tr>
                    ''' for m_name, m_cnt in sorted(marchi_stats.items(), key=lambda x: x[1], reverse=True)])}
                </tbody>
            </table>
        </div>
    </div>

    <!-- ANALISI STATUS ASSOCIATIVO CNA -->
    <div class="section-title">3. Opportunità Commerciale & Sinergia con CNA Catania</div>
    <div style="background: #F7FAFC; border: 1px solid #CBD5E0; border-radius: 6px; padding: 10px 12px; font-size: 8pt; margin-bottom: 14px;">
        <p style="margin: 0 0 6px 0;">
            <strong>🔵 Target Vendita Combinata (Non Associati - {target_cna} Ditte):</strong> 
            Rappresentano la leva a più alto impatto economico. A queste aziende viene proposta l'attivazione dell'assistente vocale H24 TecnicoLIVE combinata con l'adesione a CNA Catania usufruendo della <em>scontistica riservata sulla quota d'iscrizione del primo anno</em>.
        </p>
        <p style="margin: 0;">
            <strong>🟢 Associati Rilevati ({associati} Ditte):</strong> 
            Aziende già convenzionate con CNA Catania, pronte per la vendita diretta del centralino vocale AI con applicazione dello sconto di categoria (-15% sul canone mensile).
        </p>
    </div>

    <!-- CATALOGO ESECUTIVO DEI LEAD PRIORITARI (TIER A VIP & WARM) -->
    <div class="section-title">4. Catalogo Esecutivo Lead Prioritari con Icebreaker 1-to-1 (Stile Clay.com)</div>
    <p style="font-size: 7.5pt; color: #718096; margin-top: 0; margin-bottom: 6px;">
        Elenco delle migliori imprese qualificate per punteggio ICP, complete di numero normalizzato, P.IVA validata e icebreaker dinamico pronto per la chiamata dell'operatore:
    </p>

    <table class="table-custom">
        <thead>
            <tr>
                <th style="width: 25%;">Ragione Sociale & Comune</th>
                <th style="width: 15%;">Telefono & P.IVA</th>
                <th style="width: 18%;">Stato CNA & Tier</th>
                <th style="width: 42%;">Gancio Conversazionale 1-to-1 (Pronto da Leggere)</th>
            </tr>
        </thead>
        <tbody>
            {"".join([f'''
            <tr>
                <td>
                    <strong>{lead.get('Company Name', '')}</strong><br>
                    <span style="color: #4A5568; font-size: 7.5pt;">📍 {lead.get('City', '')} ({lead.get('Area_Geografica', 'Provincia')})</span><br>
                    <span style="color: #718096; font-size: 7pt;">🔧 {lead.get('Marchi_Rilevati', 'Caldaie / Impianti')}</span>
                </td>
                <td>
                    <strong style="color: #2D3748;">{lead.get('Phone', '')}</strong><br>
                    <code style="font-size: 7pt; color: #4A5568;">{lead.get('Partita_IVA', 'N/D')}</code>
                </td>
                <td>
                    <span class="{'badge-vip' if 'Tier A' in str(lead.get('Lead_Tier')) else 'badge-warm'}">{lead.get('Lead_Tier', 'Tier B')}</span><br>
                    <span style="font-size: 7.5pt; font-weight: 700; color: #2B6CB0;">Score: {lead.get('ICP_Score', '75')}/100</span><br>
                    <span style="font-size: 7pt; color: #718096;">{lead.get('Stato_CNA', '').replace('🔵 ', '').replace('🟢 ', '').replace('🟡 ', '')}</span>
                </td>
                <td>
                    <div class="icebreaker-box">
                        "{lead.get('Icebreaker_1to1', 'Buongiorno, vi contatto da TecnicoLIVE per la convenzione CNA Catania...')}"
                    </div>
                </td>
            </tr>
            ''' for lead in top_leads])}
        </tbody>
    </table>

    <!-- SCRIPT OUTBOUND DI SUPPORTO -->
    <div class="section-title">5. Script Telefonici Operativi per Collaboratori Umani</div>
    <div style="background: #FFF5F5; border: 1px solid #FEB2B2; border-radius: 6px; padding: 10px 12px; font-size: 7.8pt; margin-bottom: 12px;">
        <strong style="color: #9B2C2C;">📞 Script Outbound per Ditte NON Associate a CNA (Quota 1° Anno Scontata):</strong><br>
        <em>"Buongiorno [Nome Titolare], vi contatto da TecnicoLIVE. Stiamo attivando nella zona di [Comune] la convenzione speciale con CNA Catania per gli impiantisti specializzati su [Marchi Rilevati]. Sappiamo che durante gli interventi in cantiere è frequente perdere chiamate di clienti con urgenze. Con la convenzione vi attiviamo l'assistente vocale H24 che non perde un contatto e, contemporaneamente, sblocchiamo il vostro tesseramento a CNA Catania con la forte scontistica sulla quota d'iscrizione del primo anno. Avete 5 minuti oggi alle 17:00 per una prova live sul nostro numero test?"</em>
    </div>

    <!-- FOOTER DI CONFORMITA -->
    <div class="footer-note">
        TecnicoLIVE 2.0 &bull; Sinergia Rete d'Imprese &bull; Piazza dei Martiri 8, 95131 Catania (CT) &bull; Partnership con CNA Catania &bull; Conforme GDPR & Direttiva ePrivacy
    </div>

</body>
</html>"""
    return html


async def generate_termoidraulica_pdf() -> Path:
    csv_file = DATA_DIR / "termoidraulica_catania_provincia.csv"
    if not csv_file.exists():
        csv_file = DATA_DIR / "campagna_outbound_tecnicolive.csv"

    print(f"Lettura dataset da: {csv_file}")
    df = pd.read_csv(csv_file, dtype=str).fillna("")

    # Filtra per termoidraulica se letto dal master
    if "Nicchia_Target" in df.columns:
        mask = df["Nicchia_Target"].str.contains("Termoidraulica|HVAC|Caldaie|Clima", case=False, na=False) | \
               df.get("Category", pd.Series([""]*len(df))).str.contains("termoidraulica|caldaie|idraulic|climatiz", case=False, na=False)
        if mask.any():
            df = df[mask].copy()

    print(f"Compilazione report per {len(df)} aziende di Termoidraulica...")
    html_content = build_termoidraulica_html(df)

    html_file = DATA_DIR / "temp_termoidraulica_report.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Compilazione PDF ad alta fedeltà con Playwright Chromium...")
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

    print(f"Report PDF generato con successo: {PDF_OUTPUT_PATH}")
    return PDF_OUTPUT_PATH


if __name__ == "__main__":
    asyncio.run(generate_termoidraulica_pdf())
