import asyncio
import html as html_lib
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright

from src.config import (
    DATA_DIR,
    DEFAULT_ARPU_MONTHLY,
    DEFAULT_PRO_ANNUAL_MONTHLY,
    DEFAULT_SETUP_FEE_PRO,
    GDPR_OPTOUT_TEXT,
    OUTPUT_DA_ARRICCHIRE_CSV,
    OUTPUT_DASHBOARD_CSV,
    OUTPUT_OUTBOUND_CSV,
    PDF_REPORT_FILE,
    PRICING_PLANS,
    SENDER_IDENTITY,
)

PDF_OUTPUT_PATH = PDF_REPORT_FILE


def _esc(val) -> str:
    return html_lib.escape("" if val is None else str(val), quote=True)


def build_html_report(stats: dict, associati: list, top_targets: list, niche_counts: dict) -> str:
    target_count = max(0, int(stats.get("target_nuovi", 0)))
    totale_lead = max(1, int(stats.get("totale", 1)))
    chiamabili_count = int(stats.get("chiamabili", stats.get("totale", 0)))
    da_arricchire_count = int(stats.get("da_arricchire", 0))

    # Calcoli proiezioni economiche TecnicoLIVE con listino ufficiale Piano Pro (MODELLO PREDITTIVO)
    arpu = DEFAULT_ARPU_MONTHLY              # 269 €/mese Piano Pro mensile
    arpu_annuale = DEFAULT_PRO_ANNUAL_MONTHLY  # 215.20 €/mese Piano Pro annuale (-20%)
    setup_fee = DEFAULT_SETUP_FEE_PRO        # 599 € Setup Fee Piano Pro
    churn_monthly = 0.021                    # 2.1% churn rate mensile ipotizzato (STIMA TEORICA)
    customer_lifetime_months = round(1 / churn_monthly, 1)  # ~47.6 mesi
    ltv = round(arpu * customer_lifetime_months, 0)

    # Scenari basati sui target chiamabili con P.IVA e telefono E.164
    base_targets = max(1, int(stats.get("target_chiamabili", target_count)))
    scen_cons_clients = max(1, round(base_targets * 0.05))
    scen_cons_mrr = scen_cons_clients * arpu
    scen_cons_arr = scen_cons_mrr * 12

    scen_mod_clients = max(2, round(base_targets * 0.12))
    scen_mod_mrr = scen_mod_clients * arpu
    scen_mod_arr = scen_mod_mrr * 12

    scen_opt_clients = max(4, round(base_targets * 0.25))
    scen_opt_mrr = scen_opt_clients * arpu
    scen_opt_arr = scen_opt_mrr * 12

    associati_rows = ""
    if associati:
        associati_rows = "".join(
            f"""
            <tr>
                <td><strong>{_esc(a.get('Company Name', ''))}</strong></td>
                <td>{_esc(a.get('City', ''))}</td>
                <td><code>{_esc(a.get('Phone', '') or 'Da arricchire')}</code></td>
                <td><code>{_esc(a.get('Partita_IVA', ''))}</code></td>
                <td><span class="tag-green">{_esc(a.get('Evidenza_CNA', ''))}</span></td>
                <td>Onboarding Diretto Soci CNA</td>
            </tr>
            """
            for a in associati
        )
    else:
        associati_rows = '<tr><td colspan="6" style="text-align:center;color:#718096;">Nessun socio CNA rilevato automaticamente nel sottoinsieme corrente.</td></tr>'

    target_rows = "".join(
        f"""
        <tr>
            <td><strong>{_esc(t.get('Company Name', ''))}</strong></td>
            <td>{_esc(t.get('Nicchia_Target', ''))}</td>
            <td>{_esc(t.get('City', ''))}</td>
            <td><code>{_esc(t.get('Phone', ''))}</code></td>
            <td><code>{_esc(t.get('Partita_IVA', ''))}</code></td>
            <td><span class="tag-blue">TARGET CNA 50% 1° ANNO</span></td>
        </tr>
        """
        for t in top_targets
    )

    niche_rows = "".join(
        f"""
        <div class="niche-row">
            <div class="niche-name">{_esc(niche)}</div>
            <div class="niche-bar-outer">
                <div class="niche-bar-inner" style="width: {(count / totale_lead * 100):.1f}%;"></div>
            </div>
            <div class="niche-count">{count} ditte ({(count / totale_lead * 100):.1f}%)</div>
        </div>
        """
        for niche, count in niche_counts.items()
    )

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
            font-size: 9.2pt;
        }}
        .header {{
            border-bottom: 2px solid #005A9E;
            padding-bottom: 10px;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .brand-title {{
            font-size: 18pt;
            font-weight: 800;
            color: #0A2540;
            margin: 0;
            letter-spacing: -0.5px;
        }}
        .brand-subtitle {{
            font-size: 9.5pt;
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
            margin-bottom: 14px;
        }}
        .kpi-card {{
            background: #F7FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 9px;
            text-align: center;
        }}
        .kpi-card.highlight {{
            background: #EBF8FF;
            border-color: #3182CE;
        }}
        .kpi-val {{
            font-size: 17pt;
            font-weight: 800;
            color: #1A365D;
            line-height: 1.1;
        }}
        .kpi-lbl {{
            font-size: 7.2pt;
            text-transform: uppercase;
            font-weight: 700;
            color: #718096;
            margin-top: 3px;
        }}
        .section-title {{
            font-size: 10.5pt;
            font-weight: 800;
            color: #1A202C;
            border-left: 4px solid #005A9E;
            padding-left: 8px;
            margin-top: 16px;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }}
        .summary-box {{
            background: #EDF2F7;
            border-radius: 6px;
            padding: 9px 12px;
            font-size: 8.6pt;
            margin-bottom: 14px;
            border-left: 4px solid #4A5568;
        }}
        .table-custom {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8.2pt;
            margin-bottom: 14px;
        }}
        .table-custom th {{
            background: #1A365D;
            color: #FFFFFF;
            text-align: left;
            padding: 5px 7px;
            font-weight: 700;
            font-size: 7.2pt;
            text-transform: uppercase;
        }}
        .table-custom td {{
            padding: 4.5px 7px;
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
            margin-bottom: 12px;
        }}
        .niche-row {{
            display: flex;
            align-items: center;
            margin-bottom: 5px;
            font-size: 8.3pt;
        }}
        .niche-name {{
            width: 190px;
            font-weight: 600;
        }}
        .niche-bar-outer {{
            flex-grow: 1;
            background: #EDF2F7;
            height: 13px;
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
            width: 105px;
            text-align: right;
            font-weight: 700;
            color: #2B6CB0;
        }}
        .fin-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 12px;
        }}
        .fin-card {{
            border-radius: 6px;
            padding: 9px;
            border: 1px solid #E2E8F0;
            background: #FFFFFF;
        }}
        .fin-card.conservative {{ border-top: 4px solid #A0AEC0; }}
        .fin-card.moderate {{ border-top: 4px solid #3182CE; background: #F7FAFC; }}
        .fin-card.optimal {{ border-top: 4px solid #38A169; background: #F0FFF4; }}
        .fin-scenario {{
            font-size: 7.8pt;
            font-weight: 800;
            text-transform: uppercase;
            color: #4A5568;
            margin-bottom: 4px;
        }}
        .fin-mrr {{
            font-size: 15pt;
            font-weight: 800;
            color: #1A202C;
            line-height: 1.1;
        }}
        .fin-arr {{
            font-size: 8.2pt;
            color: #718096;
            margin-top: 2px;
        }}
        .fin-detail {{
            font-size: 7.8pt;
            color: #4A5568;
            margin-top: 5px;
            border-top: 1px dashed #CBD5E0;
            padding-top: 4px;
        }}
        .churn-box {{
            background: #FFF5F5;
            border: 1px solid #FEB2B2;
            border-radius: 6px;
            padding: 9px 12px;
            margin-bottom: 12px;
            font-size: 8.2pt;
        }}
        .guide-box {{
            background: #F7FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 6px;
            padding: 9px 12px;
            margin-bottom: 12px;
            font-size: 8.2pt;
        }}
        .page-break {{ page-break-before: always; }}
        .footer-note {{
            margin-top: 14px;
            border-top: 1px solid #E2E8F0;
            padding-top: 8px;
            font-size: 7.3pt;
            color: #718096;
            text-align: center;
        }}
    </style>
</head>
<body>

    <div class="header">
        <div>
            <div class="brand-title">TECNICOLIVE &bull; REPORT STRATEGICO & FINANZIARIO</div>
            <div class="brand-subtitle">Censimento Territoriale Impiantisti & Proiezioni SaaS CNA Catania</div>
        </div>
        <div class="badge-box">
            <span class="badge">PROGETTO CATANIA 2026</span><br>
            <strong>Listino Ufficiale:</strong> Base 169€ &bull; Pro 269€ &bull; Business 369€<br>
            <strong>Partner:</strong> CNA Territoriale Catania (50% 1° Anno)
        </div>
    </div>

    <div class="summary-box">
        <strong>Inquadramento Commerciale & Listino Ufficiale:</strong> Il censimento mappa le imprese impiantistiche pulite della Città Metropolitana di Catania
        (<strong>{stats.get('totale', 0)} aziende totali</strong>, di cui <strong>{chiamabili_count} chiamabili con telefono E.164</strong> e <strong>{da_arricchire_count} da arricchire</strong>).
        Listino ufficiale: <strong>Base {PRICING_PLANS['base']['monthly']}€/m</strong> (+{PRICING_PLANS['base']['setup_fee']}€ setup, {PRICING_PLANS['base']['minutes']} min),
        <strong>Pro {PRICING_PLANS['pro']['monthly']}€/m</strong> (+{PRICING_PLANS['pro']['setup_fee']}€ setup, {PRICING_PLANS['pro']['minutes']} min),
        <strong>Business {PRICING_PLANS['business']['monthly']}€/m</strong> (+{PRICING_PLANS['business']['setup_fee']}€ setup, {PRICING_PLANS['business']['minutes']} min), annuale <strong>-20%</strong>.
        Convenzione CNA Catania: <strong>associazione a CNA al 50% per tutto il 1° anno</strong> per i non associati.
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-val">{stats.get('totale', 0)}</div>
            <div class="kpi-lbl">Imprese Pulite ({chiamabili_count} E.164)</div>
        </div>
        <div class="kpi-card highlight">
            <div class="kpi-val">{stats.get('piva_valide', 0)}</div>
            <div class="kpi-lbl">P.IVA Validate (IT)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-val" style="color: #276749;">{stats.get('associati_cna', 0)}</div>
            <div class="kpi-lbl">Soci CNA Rilevati</div>
        </div>
        <div class="kpi-card highlight">
            <div class="kpi-val" style="color: #2B6CB0;">{target_count}</div>
            <div class="kpi-lbl">Target CNA (50% 1° Anno)</div>
        </div>
    </div>

    <div class="section-title">1. MODELLO PREDITTIVO / STIMA TEORICA — Proiezioni SaaS (Piano Pro {arpu}€/mese)</div>
    <div class="fin-grid">
        <div class="fin-card conservative">
            <div class="fin-scenario">STIMA TEORICA • Scenario Conservativo (5%)</div>
            <div class="fin-mrr">{scen_cons_mrr:,} € <span style="font-size: 8.5pt; font-weight: normal;">/mese MRR</span></div>
            <div class="fin-arr"><strong>{scen_cons_arr:,} €</strong> ARR Annuo Stimato</div>
            <div class="fin-detail">
                <strong>{scen_cons_clients} Clienti Ipotizzati</strong> (su {base_targets} chiamabili)<br>
                Setup Fees Pro (+{setup_fee}€): +{scen_cons_clients * setup_fee:,} €
            </div>
        </div>
        <div class="fin-card moderate">
            <div class="fin-scenario">STIMA TEORICA • Scenario Moderato (12%)</div>
            <div class="fin-mrr" style="color: #2B6CB0;">{scen_mod_mrr:,} € <span style="font-size: 8.5pt; font-weight: normal;">/mese MRR</span></div>
            <div class="fin-arr"><strong>{scen_mod_arr:,} €</strong> ARR Annuo Stimato</div>
            <div class="fin-detail">
                <strong>{scen_mod_clients} Clienti Ipotizzati</strong> (Piano annuale -20%: {arpu_annuale:.2f}€/m)<br>
                Setup Fees Pro (+{setup_fee}€): +{scen_mod_clients * setup_fee:,} €
            </div>
        </div>
        <div class="fin-card optimal">
            <div class="fin-scenario">STIMA TEORICA • Scenario Ottimale (25%)</div>
            <div class="fin-mrr" style="color: #22543D;">{scen_opt_mrr:,} € <span style="font-size: 8.5pt; font-weight: normal;">/mese MRR</span></div>
            <div class="fin-arr"><strong>{scen_opt_arr:,} €</strong> ARR Annuo Stimato</div>
            <div class="fin-detail">
                <strong>{scen_opt_clients} Clienti Ipotizzati</strong><br>
                Setup Fees Pro (+{setup_fee}€): +{scen_opt_clients * setup_fee:,} €
            </div>
        </div>
    </div>

    <div class="churn-box">
        <strong>MODELLO PREDITTIVO (STIMA TEORICA) — Churn Rate & Lifetime Value (LTV):</strong>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 5px;">
            <div>&bull; <strong>Churn Mensile Ipotizzato:</strong> <code>{churn_monthly*100:.1f}%</code> (ipotesi modello)</div>
            <div>&bull; <strong>Permanenza Teorica:</strong> <code>{customer_lifetime_months} mesi</code></div>
            <div>&bull; <strong>LTV Teorico (ARPU {arpu}€):</strong> <code>{ltv:,.0f} €</code> / azienda</div>
        </div>
        <p style="margin: 5px 0 0 0; font-size: 7.8pt; color: #742A2A;">
            <em>Nota metodologica (AGENTS.md §2):</em> Valori calcolati come modello teorico di piano finanziario, soggetti a verifica sulle conversioni reali di campagna.
        </p>
    </div>

    <div class="section-title">2. Distribuzione per Settore e Nicchia Operativa (Totale Pulito)</div>
    <div class="niche-bar-container">
        {niche_rows}
    </div>

    <div class="section-title">3. Imprese già Associate a CNA Catania Rilevate</div>
    <table class="table-custom">
        <thead>
            <tr>
                <th>Ragione Sociale</th>
                <th>Comune</th>
                <th>Telefono (E.164)</th>
                <th>Partita IVA</th>
                <th>Evidenza Riscontrata</th>
                <th>Azione Commerciale</th>
            </tr>
        </thead>
        <tbody>
            {associati_rows}
        </tbody>
    </table>

    <div class="page-break"></div>

    <div class="header" style="margin-top: 8px;">
        <div>
            <div class="brand-title" style="font-size: 14pt;">TECNICOLIVE &bull; REPORT OPERATIVO (PAGINA 2)</div>
            <div class="brand-subtitle">Lead Chiamabili Prioritari & Target Associazione CNA (50% 1° Anno)</div>
        </div>
        <div class="badge-box"><strong>Provincia di Catania</strong> | E.164 Verified</div>
    </div>

    <div class="guide-box">
        <strong>Standard di Igiene Dati Applicati:</strong>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 4px;">
            <div>&bull; <strong>Partita IVA (IT):</strong> 11 cifre validate matematicamente con algoritmo di Luhn (DPR 633/1972). Zero GDO/retail.</div>
            <div>&bull; <strong>Telefono E.164:</strong> Tutti i recapiti in <code>campagna_outbound_tecnicolive.csv</code> sono normalizzati in <code>+39...</code>.</div>
            <div>&bull; <strong>Stato CNA:</strong> <span class="tag-green">Socio Rilevato</span> vs <span class="tag-blue">Target Non Associato (50% 1° anno CNA)</span>.</div>
        </div>
    </div>

    <div class="section-title">4. Top Lead Chiamabili per Tesseramento CNA (con Telefono E.164 & P.IVA)</div>
    <p style="font-size: 7.8pt; color: #4A5568; margin-bottom: 6px;">
        Estratto da <code>data/campagna_outbound_tecnicolive.csv</code>: aziende impiantistiche con P.IVA certificata e recapito E.164 verificato:
    </p>
    <table class="table-custom">
        <thead>
            <tr>
                <th>Ragione Sociale</th>
                <th>Nicchia</th>
                <th>Comune</th>
                <th>Telefono (E.164)</th>
                <th>Partita IVA (IT)</th>
                <th>Stato Commerciale</th>
            </tr>
        </thead>
        <tbody>
            {target_rows}
        </tbody>
    </table>

    <div class="section-title">5. Sinergia Istituzionale, Ufficio Soci CNA & Conformità GDPR</div>
    <div style="background: #F0FFF4; border: 1px solid #9AE6B4; border-radius: 6px; padding: 9px 12px; font-size: 8.2pt;">
        <p style="margin: 0 0 4px 0;">
            1. <strong>Riscontro Ufficio Soci:</strong> Il file <code>data/richiesta_verifica_cna.csv</code> è sincronizzato per la spunta ufficiale presso CNA Catania (Piazza dei Martiri 8).
        </p>
        <p style="margin: 0 0 4px 0;">
            2. <strong>Human-in-the-Loop & Opt-Out (`AGENTS.md`):</strong> Nessun messaggio viene inviato automaticamente senza approvazione umana. Tutti i draft in <code>campagna_outbound_tecnicolive.csv</code> includono identificazione mittente e opt-out: <em>"{_esc(GDPR_OPTOUT_TEXT)}"</em>
        </p>
    </div>

    <div class="footer-note">
        {_esc(SENDER_IDENTITY)}
    </div>

</body>
</html>"""
    return html


async def generate_pdf() -> Path:
    print("Caricamento dataset sincronizzati...")
    source_all = OUTPUT_DASHBOARD_CSV if OUTPUT_DASHBOARD_CSV.exists() else (DATA_DIR / "campagna_outbound_tecnicolive.csv")
    df_all = pd.read_csv(source_all, dtype=str).fillna("")

    df_outbound = (
        pd.read_csv(OUTPUT_OUTBOUND_CSV, dtype=str).fillna("")
        if OUTPUT_OUTBOUND_CSV.exists()
        else df_all[df_all["Phone"].str.strip() != ""].copy()
    )
    da_arricchire_cnt = (
        len(pd.read_csv(OUTPUT_DA_ARRICCHIRE_CSV, dtype=str))
        if OUTPUT_DA_ARRICCHIRE_CSV.exists()
        else int((df_all["Phone"].str.strip() == "").sum())
    )

    totale = len(df_all)
    piva_valide = int(df_all["Partita_IVA"].fillna("").astype(str).str.startswith("IT").sum())
    associati_df = df_all[df_all["Stato_CNA"].str.contains("ASSOCIATO RILEVATO", na=False)]
    target_all_df = df_all[df_all["Stato_CNA"].str.contains("NON ASSOCIATO", na=False)]
    target_callable_df = df_outbound[df_outbound["Stato_CNA"].str.contains("NON ASSOCIATO", na=False)]

    stats = {
        "totale": totale,
        "chiamabili": len(df_outbound),
        "da_arricchire": da_arricchire_cnt,
        "piva_valide": piva_valide,
        "associati_cna": len(associati_df),
        "target_nuovi": len(target_all_df),
        "target_chiamabili": len(target_callable_df),
    }

    associati = associati_df.to_dict(orient="records")
    top_targets = target_callable_df.head(15).to_dict(orient="records")
    niche_counts = df_all["Nicchia_Target"].value_counts().to_dict()

    html_content = build_html_report(stats, associati, top_targets, niche_counts)

    html_file = DATA_DIR / "report_temp.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Compilazione PDF Strategico con Playwright Chromium...")
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

    print(f"PDF Strategico generato con successo: {PDF_OUTPUT_PATH}")
    return PDF_OUTPUT_PATH


if __name__ == "__main__":
    asyncio.run(generate_pdf())
