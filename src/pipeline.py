import asyncio
import logging
import re
from typing import Any, Dict, List

import aiohttp
import pandas as pd
from crawl4ai import AsyncWebCrawler
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.config import (
    CSV_DIR,
    DATA_DIR,
    EXCEL_DIR,
    GDPR_OPTOUT_TEXT,
    OUTPUT_ASSOCIATI_CSV,
    OUTPUT_CSV_ENRICHED,
    OUTPUT_DA_ARRICCHIRE_CSV,
    OUTPUT_DASHBOARD_CSV,
    OUTPUT_DASHBOARD_EXCEL,
    OUTPUT_OUTBOUND_CSV,
    OUTPUT_RIEPILOGO_CSV,
    OUTPUT_TARGET_CSV,
    OUTPUT_TERMOIDRAULICA_CSV,
    OUTPUT_VERIFICA_CNA_CSV,
    OUTPUT_VERIFICA_CNA_EXCEL,
    SENDER_IDENTITY,
)
from src.normalizers import (
    clean_company_website,
    is_anti_persona_retail,
    is_maltese_or_foreign_record,
    is_strict_e164_italian,
    is_valid_company_website,
    normalize_city_and_area,
    normalize_email,
    normalize_phone_e164,
)
from src.osint_fallback import osint_find_piva
from src.website_crawler import fetch_website_intelligence

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pipeline")


def is_maltese_or_foreign(row: pd.Series) -> bool:
    """Wrapper Pandas compatibile per verificare dati maltesi (+356 / MT) o esteri."""
    return is_maltese_or_foreign_record(row.to_dict())


def format_phone(val: Any) -> str:
    """Normalizza un numero di telefono italiano nel formato stretto E.164 (es. '+390957704550')."""
    primary, _ = normalize_phone_e164(val)
    return primary


def generate_outbound_pitch(comp_name: str, niche: str, stato_cna: str, city: str) -> str:
    """Genera l'aggancio telefonico conforme a AGENTS.md e alla convenzione CNA al 50% per il 1° anno."""
    clean_city = city.strip() if city else "Catania"
    clean_niche = niche.strip() if niche else "impiantistica"
    if "ASSOCIATO RILEVATO" in str(stato_cna):
        return (
            f"Buongiorno {comp_name}, vi contattiamo da {SENDER_IDENTITY}. "
            f"In quanto azienda di {clean_niche} operante a {clean_city} collegata a CNA Catania, "
            f"potete attivare l'assistente vocale AI TecnicoLIVE per non perdere chiamate in cantiere "
            f"e ricevere le schede intervento direttamente su WhatsApp. {GDPR_OPTOUT_TEXT}"
        )
    return (
        f"Buongiorno {comp_name}, vi contattiamo da {SENDER_IDENTITY}. "
        f"Stiamo supportando le aziende di {clean_niche} a {clean_city} con la convenzione ufficiale CNA Catania: "
        f"attiviamo l'assistente vocale per recuperare gli interventi persi in cantiere e sblocchiamo "
        f"l'associazione a CNA Catania al 50% della quota per tutto il primo anno. {GDPR_OPTOUT_TEXT}"
    )


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

            before = len(df)
            df = df[~df.apply(is_maltese_or_foreign, axis=1)]
            df = df[
                ~df.apply(
                    lambda r: is_anti_persona_retail(
                        r.get("Company Name", ""), r.get("Category", ""), r.get("Website", "")
                    ),
                    axis=1,
                )
            ]
            after = len(df)
            if before != after:
                logger.info(f"Decontaminato {filename}: rimossi {before - after} record esteri/GDO non in target.")

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
    """Esegue la pipeline di scansione P.IVA, siti web reali e verifica CNA sulle lead sorgenti."""
    from src.clay_engine import enrich_dataset_with_clay_engine

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
                website = clean_company_website(row.get("Website", ""))
                city_raw = row.get("City", "").strip() or "Catania"
                address = row.get("Address", "").strip()
                city, area = normalize_city_and_area(city_raw, address)
                phone_primary, phone_secondary = normalize_phone_e164(row.get("Phone", ""))
                niche = row.get("Nicchia_Target", "")

                logger.info(f"[{idx+1}/{len(df)}] Elaborazione: {comp_name} ({city}) - Web: {website or 'NO'}")

                crawl_res = await fetch_website_intelligence(session, website, crawler=crawler)
                piva = crawl_res.get("piva")
                piva_source = crawl_res.get("piva_source")
                cna_affiliato = crawl_res.get("cna_affiliato", False)
                cna_dettaglio = crawl_res.get("cna_dettaglio", "")
                text_snippet = crawl_res.get("text_snippet", "")
                found_email = crawl_res.get("email", "")
                found_phone = crawl_res.get("phone", "")

                if not phone_primary and found_phone:
                    phone_primary = found_phone

                if not piva:
                    osint_res = await osint_find_piva(session, comp_name, city, address)
                    if osint_res.get("piva"):
                        piva = osint_res["piva"]
                        piva_source = osint_res["piva_source"]
                    if not cna_affiliato and osint_res.get("cna_affiliato"):
                        cna_affiliato = True
                        cna_dettaglio = osint_res.get("cna_dettaglio", "")

                piva_formatted = f"IT{piva}" if piva else ""

                if cna_affiliato:
                    stato_cna = "🟢 ASSOCIATO RILEVATO (Convenzione TecnicoLIVE)"
                    azione_commerciale = "Proporre assistente vocale AI TecnicoLIVE per soci CNA Catania"
                elif piva:
                    stato_cna = "🔵 NON ASSOCIATO (Target Tesseramento CNA)"
                    azione_commerciale = "Proporre TecnicoLIVE + Iscrizione CNA Catania al 50% per il 1° anno"
                else:
                    stato_cna = "🟡 DA VERIFICARE (P.IVA mancante)"
                    azione_commerciale = "Verificare manualmente P.IVA per controllo con Ufficio Soci CNA"

                row_dict = row.to_dict()
                row_dict["City"] = city
                row_dict["Area_Geografica"] = area
                row_dict["Phone"] = phone_primary
                row_dict["Phone_Secondary"] = phone_secondary
                row_dict["Website"] = website
                row_dict["Email"] = normalize_email(row.get("Email", "")) or found_email
                row_dict["Partita_IVA"] = piva_formatted
                row_dict["P_IVA_Numerica"] = piva or ""
                row_dict["Fonte_PIVA"] = piva_source
                row_dict["Stato_CNA"] = stato_cna
                row_dict["Evidenza_CNA"] = cna_dettaglio
                row_dict["Azione_Commerciale_Consigliata"] = azione_commerciale
                row_dict["Website_Text_Snippet"] = text_snippet
                row_dict["Pitch_Commerciale_TecnicoLIVE"] = generate_outbound_pitch(
                    comp_name, niche, stato_cna, city
                )

                enriched_rows.append(row_dict)
                await asyncio.sleep(0.2)

    enriched_df = pd.DataFrame(enriched_rows)
    return enrich_dataset_with_clay_engine(enriched_df)


def _style_excel_workbook(path, header_color: str = "1F4E78"):
    wb = load_workbook(path)
    header_fill = PatternFill(start_color=header_color, end_color=header_color, fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    for ws in wb.worksheets:
        ws.views.sheetView[0].showGridLines = True
        for col_idx, col in enumerate(ws.iter_cols(min_row=1, max_row=ws.max_row), start=1):
            cell = col[0]
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            max_len = max((len(str(c.value or "")) for c in col), default=12)
            col_letter = get_column_letter(col_idx)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 48)
    wb.save(path)


def export_all_outputs(df: pd.DataFrame) -> Dict[str, int]:
    """
    Esporta in modo atomico e sincronizzato TUTTI i CSV (in data/) e TUTTI gli Excel (in exports_excel/)
    a partire dal singolo dataset master pulito.
    """
    from src.clay_engine import enrich_dataset_with_clay_engine

    DATA_DIR.mkdir(exist_ok=True)
    EXCEL_DIR.mkdir(exist_ok=True)

    work = df.copy()
    if work.empty:
        return {"totale": 0}

    # Filtro di sicurezza geografico e anti-GDO
    work = work[~work.apply(is_maltese_or_foreign, axis=1)].copy()
    work = work[
        ~work.apply(
            lambda r: is_anti_persona_retail(
                r.get("Company Name", ""), r.get("Category", ""), r.get("Website", "")
            ),
            axis=1,
        )
    ].copy()

    # Normalizzazione garantita di telefoni, email, siti, città/area
    phones_norm = work.apply(
        lambda r: normalize_phone_e164(
            f"{r.get('Phone', '')} / {r.get('Phone_Secondary', '')}" if r.get("Phone_Secondary") else r.get("Phone", "")
        ),
        axis=1,
    )
    work["Phone"] = [p[0] for p in phones_norm]
    work["Phone_Secondary"] = [p[1] for p in phones_norm]
    work["Contatto_Chiamabile"] = work["Phone"].apply(lambda p: "SI" if is_strict_e164_italian(p) else "NO")

    if "Website" in work.columns:
        work["Website"] = work["Website"].apply(clean_company_website)
    else:
        work["Website"] = ""

    if "Email" in work.columns:
        work["Email"] = work["Email"].apply(normalize_email)
    else:
        work["Email"] = ""

    city_area = work.apply(
        lambda r: normalize_city_and_area(r.get("City", ""), r.get("Address", "")),
        axis=1,
    )
    work["City"] = [ca[0] for ca in city_area]
    work["Area_Geografica"] = [ca[1] for ca in city_area]

    # Assicura colonna Pitch e ri-arricchisce con Clay Engine (Zero Hallucination)
    for col in ("Category", "Address", "Partita_IVA", "Stato_CNA", "Evidenza_CNA", "Azione_Commerciale_Consigliata", "Fonte_PIVA"):
        if col not in work.columns:
            work[col] = ""

    work = enrich_dataset_with_clay_engine(work)
    work["Pitch_Commerciale_TecnicoLIVE"] = work.apply(
        lambda r: generate_outbound_pitch(
            r.get("Company Name", ""), r.get("Nicchia_Target", ""), r.get("Stato_CNA", ""), r.get("City", "")
        ),
        axis=1,
    )

    # Ordina: chiamabili prima, poi ICP_Score decrescente, poi P.IVA, poi nome
    work["_score_num"] = pd.to_numeric(work["ICP_Score"], errors="coerce").fillna(0)
    work["_call_ord"] = work["Contatto_Chiamabile"].apply(lambda x: 1 if x == "SI" else 0)
    work = work.sort_values(
        by=["_call_ord", "_score_num", "Partita_IVA", "Company Name"],
        ascending=[False, False, False, True],
    )
    work.drop(columns=["_score_num", "_call_ord"], inplace=True)
    work.reset_index(drop=True, inplace=True)

    # Esporta master completo (senza il corpus raw testuale gigante nei CSV operativi)
    full_export = work.drop(columns=[c for c in ("Website_Text_Snippet",) if c in work.columns]).copy()
    full_export.to_csv(OUTPUT_CSV_ENRICHED, index=False, encoding="utf-8-sig")

    dash_cols = [
        "Company Name", "Nicchia_Target", "City", "Area_Geografica", "Phone", "Phone_Secondary",
        "Contatto_Chiamabile", "Email", "Partita_IVA", "Stato_CNA", "ICP_Score", "Lead_Tier",
        "Marchi_Rilevati", "Marchi_Verificati", "Certificazioni_Rilevate", "Servizio_H24",
        "Trigger_Segnale", "Icebreaker_1to1", "Footer_GDPR_OptOut", "Messaggio_WhatsApp_Completo",
        "Pitch_Commerciale_TecnicoLIVE", "Azione_Commerciale_Consigliata", "Website",
        "Fonte_PIVA", "Evidenza_CNA", "Category", "Address", "Data_Scoperta",
    ]
    for c in dash_cols:
        if c not in full_export.columns:
            full_export[c] = ""
    df_dash = full_export[dash_cols].copy()
    df_dash.to_csv(OUTPUT_DASHBOARD_CSV, index=False, encoding="utf-8-sig")

    # Campagna Outbound: SOLO contatti chiamabili con telefono E.164 valido
    df_outbound = df_dash[df_dash["Contatto_Chiamabile"] == "SI"].copy()
    df_outbound.to_csv(OUTPUT_OUTBOUND_CSV, index=False, encoding="utf-8-sig")

    # Lead senza telefono: isolate per arricchimento contatti
    df_da_arricchire = df_dash[df_dash["Contatto_Chiamabile"] == "NO"].copy()
    df_da_arricchire.to_csv(OUTPUT_DA_ARRICCHIRE_CSV, index=False, encoding="utf-8-sig")

    # Verticale Termoidraulica & HVAC
    termo_mask = (
        df_dash["Nicchia_Target"].str.contains("Termoidraulica|HVAC|Caldaie|Clima", case=False, na=False)
        | df_dash["Category"].str.contains("termoidraulica|caldaie|idraulic|climatiz|riscald", case=False, na=False)
    )
    df_termo = df_dash[termo_mask].copy()
    df_termo.to_csv(OUTPUT_TERMOIDRAULICA_CSV, index=False, encoding="utf-8-sig")

    target_df = df_dash[df_dash["Stato_CNA"].str.contains("NON ASSOCIATO", na=False)].copy()
    target_df.to_csv(OUTPUT_TARGET_CSV, index=False, encoding="utf-8-sig")

    associati_df = df_dash[df_dash["Stato_CNA"].str.contains("ASSOCIATO RILEVATO", na=False)].copy()
    associati_df.to_csv(OUTPUT_ASSOCIATI_CSV, index=False, encoding="utf-8-sig")

    # Statistiche riepilogo
    totale = len(df_dash)
    chiamabili = len(df_outbound)
    senza_tel = len(df_da_arricchire)
    piva_valide = int(df_dash["Partita_IVA"].fillna("").astype(str).str.startswith("IT").sum())
    real_webs = int(df_dash["Website"].apply(is_valid_company_website).sum())
    tier_a = int(df_dash["Lead_Tier"].str.contains("Tier A", na=False).sum())
    tier_b = int(df_dash["Lead_Tier"].str.contains("Tier B", na=False).sum())
    tier_c = int(df_dash["Lead_Tier"].str.contains("Tier C", na=False).sum())
    marchi_verif = int((df_dash["Marchi_Verificati"] == "SI").sum())

    stats_df = pd.DataFrame(
        {
            "Metrica": [
                "Totale Imprese Pulite (No GDO / No Estero)",
                "Lead Chiamabili (Telefono E.164 Valido)",
                "Lead Senza Telefono (in da_arricchire_contatti.csv)",
                "Partite IVA Validate Luhn (IT)",
                "% Copertura P.IVA",
                "Siti Web Aziendali Reali (No Portali)",
                "Marchi Reali Verificati",
                "Associati CNA Rilevati",
                "Target Tesseramento CNA (50% 1° Anno)",
                "Lead da Verificare (P.IVA mancante / CNA pendente)",
                "Tier A VIP (Score >= 80)",
                "Tier B Warm (Score 55-79)",
                "Tier C Cold / Da Arricchire (Score < 55)",
            ],
            "Valore": [
                totale,
                chiamabili,
                senza_tel,
                piva_valide,
                f"{(piva_valide / totale * 100):.1f}%" if totale else "0%",
                real_webs,
                marchi_verif,
                len(associati_df),
                len(target_df),
                totale - len(associati_df) - len(target_df),
                tier_a,
                tier_b,
                tier_c,
            ],
        }
    )
    stats_df.to_csv(OUTPUT_RIEPILOGO_CSV, index=False, encoding="utf-8-sig")

    # Foglio verifica Ufficio Soci CNA
    df_cna = df_dash[
        ["Company Name", "Partita_IVA", "City", "Nicchia_Target", "Phone", "Website"]
    ].copy()
    df_cna.columns = [
        "Ragione Sociale", "Partita IVA (IT)", "Comune", "Settore / Nicchia", "Telefono (E.164)", "Sito Web"
    ]
    df_cna["Socio CNA (Sì/No - a cura CNA)"] = ""
    df_cna["Note Ufficio Soci"] = ""
    df_cna.to_csv(OUTPUT_VERIFICA_CNA_CSV, index=False, encoding="utf-8-sig")

    # Esportazione Excel consolidata
    with pd.ExcelWriter(OUTPUT_DASHBOARD_EXCEL, engine="openpyxl") as writer:
        df_outbound.to_excel(writer, sheet_name="Campagna Outbound", index=False)
        df_dash.to_excel(writer, sheet_name="Tutte le Lead", index=False)
        target_df.to_excel(writer, sheet_name="Target Tesseramento CNA", index=False)
        associati_df.to_excel(writer, sheet_name="Associati Rilevati", index=False)
        df_da_arricchire.to_excel(writer, sheet_name="Da Arricchire Contatti", index=False)
        df_termo.to_excel(writer, sheet_name="Termoidraulica CT", index=False)
        stats_df.to_excel(writer, sheet_name="Riepilogo", index=False)
    _style_excel_workbook(OUTPUT_DASHBOARD_EXCEL, header_color="1F4E78")

    with pd.ExcelWriter(OUTPUT_VERIFICA_CNA_EXCEL, engine="openpyxl") as writer:
        df_cna.to_excel(writer, sheet_name="Verifica Ufficio Soci CNA", index=False)
    _style_excel_workbook(OUTPUT_VERIFICA_CNA_EXCEL, header_color="005A9E")

    logger.info(
        f"Export sincronizzato completato: {totale} totali | {chiamabili} chiamabili | "
        f"{senza_tel} da arricchire | {tier_a} Tier A | {real_webs} siti reali"
    )
    return {
        "totale": totale,
        "chiamabili": chiamabili,
        "da_arricchire": senza_tel,
        "piva_valide": piva_valide,
        "associati": len(associati_df),
        "target_cna": len(target_df),
        "tier_a": tier_a,
    }


def export_dashboard_excel(df: pd.DataFrame):
    """Alias retrocompatibile per la vecchia firma di esportazione."""
    return export_all_outputs(df)


async def run_pipeline(limit: int = 0):
    logger.info("=== Avvio Pipeline Lead Finder CNA Catania & TecnicoLIVE ===")
    enriched_df = await process_all_leads(limit=limit)
    export_all_outputs(enriched_df)
    logger.info("=== Pipeline Completata con Successo! ===")
    return enriched_df
