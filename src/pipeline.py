import asyncio
import logging
import re
from pathlib import Path
from typing import List, Dict, Any
import aiohttp
import pandas as pd
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter
from openpyxl import load_workbook

from crawl4ai import AsyncWebCrawler
from src.config import (
    CSV_DIR, DATA_DIR, EXCEL_DIR,
    OUTPUT_DASHBOARD_EXCEL, OUTPUT_VERIFICA_CNA_EXCEL,
    OUTPUT_DASHBOARD_CSV, OUTPUT_TARGET_CSV, OUTPUT_ASSOCIATI_CSV,
    OUTPUT_VERIFICA_CNA_CSV, OUTPUT_CSV_ENRICHED, OUTPUT_RIEPILOGO_CSV
)
from src.website_crawler import crawl_single_site
from src.osint_fallback import osint_find_piva
from src.piva_validator import clean_piva

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pipeline")


def is_maltese_or_foreign(row: pd.Series) -> bool:
    """Verifica se una riga contiene dati maltesi (+356 / MT) o esteri da scartare."""
    country = str(row.get("Country", "")).strip().upper()
    if country in ("MT", "MALTA", "HU"):
        return True
    
    phone = re.sub(r"[\s\.\-_]", "", str(row.get("Phone", "")))
    if re.search(r"^\+?356", phone) or "356" in phone[:6]:
        return True
        
    text = (str(row.get("City", "")) + " " + str(row.get("Address", "")) + " " + str(row.get("State", ""))).lower()
    foreign_keywords = ["malta", "gozo", "ghajnsielem", "xewkija", "qormi", "naxxar", "mellieħa", "mellieha", "mosta", "szeged"]
    if any(k in text for k in foreign_keywords):
        return True
        
    return False


def format_phone(val: Any) -> str:
    """Formatta il numero di telefono come stringa testuale pulita es. '+39 0957704550'."""
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    if s.startswith("+39"):
        return "+39 " + s[3:].strip()
    elif s.startswith("39") and len(s) > 8:
        return "+39 " + s[2:].strip()
    elif s and not s.startswith("+"):
        return s
    return s


def load_all_leads() -> pd.DataFrame:
    """Carica, unifica e decontamina tutti i 4 CSV della cartella CSV_Leads."""
    files_map = {
        "Clean_1_HVAC_Climatizzazione_Riscaldamento.csv": "HVAC & Climatizzazione",
        "Clean_2_Termoidraulica_Idraulici.csv": "Termoidraulica & Idraulica",
        "Clean_3_Impianti_Elettrici_Elettricisti.csv": "Impianti Elettrici",
        "Clean_4_Impianti_Generali_Assistenza_Altri.csv": "Impiantistica Generale",
    }
    
    dfs = []
    for filename, niche in files_map.items():
        p = CSV_DIR / filename
        if p.exists():
            df = pd.read_csv(p, dtype=str).fillna("")
            df["Nicchia_Target"] = niche
            df["Origine_File"] = filename
            
            # Filtro decontaminazione Malta (+356)
            before = len(df)
            df = df[~df.apply(is_maltese_or_foreign, axis=1)]
            after = len(df)
            if before != after:
                logger.info(f"Decontaminato {filename}: rimossi {before - after} record maltesi/esteri.")
                
            dfs.append(df)
            logger.info(f"Caricato {filename}: {len(df)} righe valide")
        else:
            logger.warning(f"File non trovato: {p}")
            
    if not dfs:
        raise FileNotFoundError(f"Nessun file CSV trovato in {CSV_DIR}")
        
    combined = pd.concat(dfs, ignore_index=True)
    combined.columns = [c.strip() for c in combined.columns]
    logger.info(f"Totale righe decontaminate caricate: {len(combined)}")
    return combined


async def process_all_leads(limit: int = 0) -> pd.DataFrame:
    """Esegue la pipeline di scansione P.IVA e verifica CNA su tutte le lead pulite."""
    df = load_all_leads()
    
    if limit > 0:
        logger.info(f"Limitazione a {limit} lead per test rapido")
        df = df.head(limit).copy()
    else:
        df = df.copy()

    enriched_rows: List[Dict[str, Any]] = []
    
    async with AsyncWebCrawler() as crawler:
        async with aiohttp.ClientSession() as session:
            for idx, row in df.iterrows():
                comp_name = row.get("Company Name", "").strip()
                website = row.get("Website", "").strip()
                city = row.get("City", "").strip() or "Catania"
                address = row.get("Address", "").strip()
                phone = format_phone(row.get("Phone", ""))
                niche = row.get("Nicchia_Target", "")
                
                logger.info(f"[{idx+1}/{len(df)}] Elaborazione: {comp_name} ({city}) - Web: {website or 'NO'}")
                
                # 1. Scansione Sito Web con Crawl4AI
                crawl_res = await crawl_single_site(crawler, website)
                
                piva = crawl_res.get("piva")
                piva_source = crawl_res.get("piva_source")
                cna_affiliato = crawl_res.get("cna_affiliato", False)
                cna_dettaglio = crawl_res.get("cna_dettaglio", "")
                
                # 2. Se P.IVA non trovata, tentiamo fallback OSINT
                if not piva:
                    osint_res = await osint_find_piva(session, comp_name, city, address)
                    if osint_res.get("piva"):
                        piva = osint_res["piva"]
                        piva_source = osint_res["piva_source"]
                    
                    if not cna_affiliato and osint_res.get("cna_affiliato"):
                        cna_affiliato = True
                        cna_dettaglio = osint_res.get("cna_dettaglio", "")
                
                piva_formatted = f"IT{piva}" if piva else ""
                
                # 3. Determinazione Stato Commerciale per TecnicoLIVE & CNA
                if cna_affiliato:
                    stato_cna = "🟢 ASSOCIATO RILEVATO (Convenzione TecnicoLIVE)"
                    azione_commerciale = "Proporre sconto/condizioni convenzione CNA Catania"
                elif piva:
                    stato_cna = "🔵 NON ASSOCIATO (Target Tesseramento CNA)"
                    azione_commerciale = "Proporre Pacchetto TecnicoLIVE + Tesseramento a CNA Catania"
                else:
                    stato_cna = "🟡 DA VERIFICARE (P.IVA mancante)"
                    azione_commerciale = "Verificare manualmente P.IVA per controllo con Ufficio Soci"

                row_dict = row.to_dict()
                row_dict["Phone"] = phone
                row_dict["Partita_IVA"] = piva_formatted
                row_dict["P_IVA_Numerica"] = piva or ""
                row_dict["Fonte_PIVA"] = piva_source
                row_dict["Stato_CNA"] = stato_cna
                row_dict["Evidenza_CNA"] = cna_dettaglio
                row_dict["Azione_Commerciale_Consigliata"] = azione_commerciale
                
                enriched_rows.append(row_dict)
                await asyncio.sleep(0.3)

    enriched_df = pd.DataFrame(enriched_rows)
    return enriched_df


def export_dashboard_excel(df: pd.DataFrame):
    """Esporta sia i CSV (in data/) che i file Excel formattati (in exports_excel/)."""
    DATA_DIR.mkdir(exist_ok=True)
    EXCEL_DIR.mkdir(exist_ok=True)
    
    # 1. Filtro di sicurezza aggiuntivo per decontaminare da numeri maltesi (+356)
    df = df[~df.apply(is_maltese_or_foreign, axis=1)].copy()
    
    if "Phone" in df.columns:
        df["Phone"] = df["Phone"].apply(format_phone)

    # 2. Esportazione file CSV dedicati (apribili nativamente nell'editor)
    df.to_csv(OUTPUT_CSV_ENRICHED, index=False, encoding="utf-8-sig")
    
    df_dash = df[[
        "Company Name", "Nicchia_Target", "City", "Phone", "Partita_IVA",
        "Stato_CNA", "Azione_Commerciale_Consigliata", "Website", "Fonte_PIVA", "Evidenza_CNA", "Address"
    ]].copy()
    df_dash.to_csv(OUTPUT_DASHBOARD_CSV, index=False, encoding="utf-8-sig")
    
    target_df = df_dash[df_dash["Stato_CNA"].str.contains("NON ASSOCIATO", na=False)]
    target_df.to_csv(OUTPUT_TARGET_CSV, index=False, encoding="utf-8-sig")
    
    associati_df = df_dash[df_dash["Stato_CNA"].str.contains("ASSOCIATO RILEVATO", na=False)]
    associati_df.to_csv(OUTPUT_ASSOCIATI_CSV, index=False, encoding="utf-8-sig")

    stats = {
        "Metrica": [
            "Totale Lead Elaborate (Solo Catania/Italia)",
            "Partite IVA Trovate e Validate",
            "% Copertura P.IVA",
            "Associati CNA Rilevati sul Web",
            "Target Nuovi da Associare a CNA",
            "Lead da Verificare con Ufficio Soci",
        ],
        "Valore": [
            len(df),
            len(df[df["Partita_IVA"].fillna("").astype(str).str.startswith("IT")]),
            f"{(len(df[df['Partita_IVA'].fillna('').astype(str).str.startswith('IT')]) / len(df) * 100):.1f}%" if len(df) else "0%",
            len(associati_df),
            len(target_df),
            len(df) - len(associati_df) - len(target_df),
        ]
    }
    pd.DataFrame(stats).to_csv(OUTPUT_RIEPILOGO_CSV, index=False, encoding="utf-8-sig")

    df_cna = df[["Company Name", "Partita_IVA", "City", "Nicchia_Target", "Phone", "Website"]].copy()
    df_cna.columns = ["Ragione Sociale", "Partita IVA (IT)", "Comune", "Settore / Nicchia", "Telefono", "Sito Web"]
    df_cna["Socio CNA (Sì/No - a cura CNA)"] = ""
    df_cna["Note Ufficio Soci"] = ""
    df_cna.to_csv(OUTPUT_VERIFICA_CNA_CSV, index=False, encoding="utf-8-sig")

    # 3. Esportazione file Excel nella cartella separata exports_excel/
    with pd.ExcelWriter(OUTPUT_DASHBOARD_EXCEL, engine="openpyxl") as writer:
        df_dash.to_excel(writer, sheet_name="Tutte le Lead", index=False)
        target_df.to_excel(writer, sheet_name="Target Tesseramento CNA", index=False)
        associati_df.to_excel(writer, sheet_name="Associati Rilevati", index=False)
        pd.DataFrame(stats).to_excel(writer, sheet_name="Riepilogo", index=False)

    wb = load_workbook(OUTPUT_DASHBOARD_EXCEL)
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    
    for ws in wb.worksheets:
        ws.views.sheetView[0].showGridLines = True
        for col_idx, col in enumerate(ws.iter_cols(min_row=1, max_row=ws.max_row), start=1):
            cell = col[0]
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            max_len = max(len(str(c.value or "")) for c in col)
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)
    wb.save(OUTPUT_DASHBOARD_EXCEL)
    logger.info(f"Dashboard Excel salvata in: {OUTPUT_DASHBOARD_EXCEL}")

    with pd.ExcelWriter(OUTPUT_VERIFICA_CNA_EXCEL, engine="openpyxl") as writer:
        df_cna.to_excel(writer, sheet_name="Verifica Ufficio Soci CNA", index=False)
        
    wb_cna = load_workbook(OUTPUT_VERIFICA_CNA_EXCEL)
    ws_cna = wb_cna.active
    ws_cna.views.sheetView[0].showGridLines = True
    cna_fill = PatternFill(start_color="005A9E", end_color="005A9E", fill_type="solid")
    for col_idx, col in enumerate(ws_cna.iter_cols(min_row=1, max_row=ws_cna.max_row), start=1):
        cell = col[0]
        cell.fill = cna_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        max_len = max(len(str(c.value or "")) for c in col)
        ws_cna.column_dimensions[get_column_letter(col_idx)].width = min(max(max_len + 3, 15), 45)
    wb_cna.save(OUTPUT_VERIFICA_CNA_EXCEL)
    logger.info(f"Foglio per verifica CNA salvato in: {OUTPUT_VERIFICA_CNA_EXCEL}")


async def run_pipeline(limit: int = 0):
    logger.info("=== Avvio Pipeline Lead Finder CNA Catania & TecnicoLIVE ===")
    enriched_df = await process_all_leads(limit=limit)
    export_dashboard_excel(enriched_df)
    logger.info("=== Pipeline Completata con Successo! ===")
    return enriched_df
