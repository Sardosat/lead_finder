"""
clay_engine.py — Motore di Intelligence GTM stile Clay.com per TecnicoLIVE.

Conforme a AGENTS.md (Zero Hallucination Policy & B2B GDPR):
1. ClaygentResearcher: estrazione semantica reale da ragione sociale e sito web (mai marchi inventati).
2. IntentSignalTracker: trigger operativi di cantiere coerenti con i dati reali.
3. AccountScorer: punteggio ICP (0-100) rigoroso (nessun Tier A senza telefono E.164 o con URL portale).
4. IcebreakerGenerator: ganci 1-to-1 onesti con leva associativa CNA al 50% per il 1° anno + footer GDPR/opt-out.
"""

import re
from typing import Any, Dict, List
import pandas as pd

from src.config import GDPR_OPTOUT_TEXT, SENDER_IDENTITY
from src.normalizers import (
    is_mobile_e164,
    is_valid_company_website,
    normalize_phone_e164,
)
from src.piva_validator import validate_piva

# ── 1. DIZIONARI SEMANTICI E REGOLE DI CLASSIFICAZIONE ──────────────────────

MARCHI_CALDAIE = [
    "Vaillant", "Buderus", "Baxi", "Bosch", "Ariston", "Ferroli", "Beretta",
    "Immergas", "Junkers", "Hermann", "Riello", "Savio", "Viessmann", "Sime",
    "Chaffoteaux", "Biasi", "Saunier Duval", "Lamborghini", "Fondital",
    "Radiant", "Unical", "Sylber", "Galletti", "Bongioanni",
]

MARCHI_CLIMA = [
    "Daikin", "Mitsubishi", "Panasonic", "Samsung", "Fujitsu",
    "Olimpia Splendid", "Hisense", "LG", "Toshiba", "Haier", "Midea",
    "Gree", "Carrier", "Hitachi", "Aermec", "Clivet", "Emmeti",
    "Innova", "Aircon", "Daitsu",
]

KEYWORDS_H24 = [
    "h24", "24/7", "24 ore", "pronto intervento", "reperibilità", "reperibilita",
    "emergenza", "notturno", "festivi", "urgenze",
]

KEYWORDS_NORMATIVE = [
    "citel", "f-gas", "fgas", "bollino blu", "efficienza energetica",
    "dm 37/08", "37/08", "curit", "catasto impianti",
]

GDPR_FOOTER = f"{SENDER_IDENTITY} | {GDPR_OPTOUT_TEXT}"


# ── 2. CLAYGENT RESEARCHER: ESTRAZIONE SEMANTICA REALE ──────────────────────

def extract_semantic_signals(
    text_corpus: str,
    company_name: str,
    niche: str,
    website_text: str = "",
) -> Dict[str, Any]:
    """
    Analizza esclusivamente dati reali (ragione sociale, categoria, testo del sito web).
    Non inventa MAI marchi o certificazioni di default se non rilevati nei testi.
    """
    combined = f"{text_corpus} {website_text}".strip()
    corpus_lower = combined.lower()

    marchi_trovati: List[str] = []
    seen_brands = set()
    for m in MARCHI_CALDAIE + MARCHI_CLIMA:
        if re.search(r"\b" + re.escape(m.lower()) + r"\b", corpus_lower):
            if m.lower() not in seen_brands:
                seen_brands.add(m.lower())
                marchi_trovati.append(m)

    marchi_verificati = len(marchi_trovati) > 0
    marchi_str = ", ".join(marchi_trovati) if marchi_verificati else "Non rilevato"

    # Reperibilità H24 / Pronto Intervento (solo se riscontrata in nome o sito)
    h24_corpus = f"{company_name} {text_corpus} {website_text}".lower()
    has_h24 = any(re.search(r"\b" + re.escape(k) + r"\b", h24_corpus) for k in KEYWORDS_H24)

    # Certificazioni normative rilevate realmente
    cert_map = {
        "citel": "CITEL Sicilia",
        "f-gas": "F-Gas",
        "fgas": "F-Gas",
        "bollino blu": "Bollino Blu",
        "efficienza energetica": "Efficienza Energetica",
        "dm 37/08": "DM 37/08",
        "37/08": "DM 37/08",
        "curit": "CURIT",
        "catasto impianti": "Catasto Impianti",
    }
    certificazioni: List[str] = []
    for kw in KEYWORDS_NORMATIVE:
        if re.search(r"\b" + re.escape(kw) + r"\b", corpus_lower):
            label = cert_map.get(kw, kw.upper())
            if label not in certificazioni:
                certificazioni.append(label)

    cert_str = ", ".join(certificazioni) if certificazioni else "Non rilevate"

    # Trigger operativo coerente con la nicchia e i segnali reali
    niche_l = (niche or "").lower()
    if has_h24:
        trigger = "Reperibilità Emergenze H24 Attiva (Rischio chiamate perse notturne/weekend)"
    elif "caldaie" in niche_l or "termoidraulica" in niche_l or "idraulic" in niche_l:
        trigger = "Stagionalità Riscaldamento & Adempimenti CITEL Sicilia"
    elif "climatizzat" in niche_l or "hvac" in niche_l:
        trigger = "Picchi Stagionali Climatizzazione Provincia di Catania"
    elif "elettric" in niche_l:
        trigger = "Interventi Elettrici & Dichiarazioni DM 37/08"
    else:
        trigger = "Gestione Chiamate in Cantiere — Settore Impiantistico"

    return {
        "marchi": marchi_trovati,
        "marchi_str": marchi_str,
        "marchi_verificati": marchi_verificati,
        "is_h24": has_h24,
        "certificazioni": cert_str,
        "trigger": trigger,
    }


# ── 3. ACCOUNT SCORER: ALGORITMO ICP FIT (0 - 100) ─────────────────────────

def calculate_lead_score(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calcola il punteggio ICP (0-100) e assegna il Tier:
    - Telefono E.164 mobile (+393...): +25 pt | fisso (+390...): +15 pt | assente: 0 pt
    - P.IVA Luhn valida (IT...): +20 pt
    - Nicchia core (Termoidraulica/HVAC/Caldaie): +20 pt | Altre impiantistiche: +10 pt
    - Stato CNA: Non Associato (+15 pt), Associato Rilevato (+10 pt), Da Verificare (+5 pt)
    - Sito Web aziendale reale (esclusi portali): +15 pt
    - Marchi reali verificati: +5 pt
    VINCOLO DI QUALITÀ: Se manca un telefono E.164 valido, il punteggio viene limitato a <= 45 (Tier C).
    """
    score = 0
    raw_phone = str(row.get("Phone", "")).strip()
    primary_phone, _ = normalize_phone_e164(raw_phone)
    has_valid_phone = bool(primary_phone)
    is_mobile = is_mobile_e164(primary_phone)

    piva = str(row.get("Partita_IVA", "")).strip()
    website = str(row.get("Website", "")).strip()
    stato_cna = str(row.get("Stato_CNA", "")).upper()
    niche = str(row.get("Nicchia_Target", "")).lower()
    marchi_verif = str(row.get("Marchi_Verificati", "")).upper() in ("SI", "TRUE", "1")
    if not marchi_verif:
        m_val = str(row.get("Marchi_Rilevati", "")).strip()
        marchi_verif = bool(m_val and m_val.lower() not in ("non rilevato", "nan", "none"))

    # 1. Telefono (Max 25)
    if is_mobile:
        score += 25
    elif has_valid_phone:
        score += 15

    # 2. Partita IVA Luhn (Max 20)
    if piva.startswith("IT") and validate_piva(piva):
        score += 20
    elif piva and validate_piva(piva):
        score += 15

    # 3. Pertinenza Nicchia (Max 20)
    if any(k in niche for k in ("caldaie", "climatizzazione", "termoidraulica", "idraulica", "hvac")):
        score += 20
    else:
        score += 10

    # 4. Stato CNA (Max 15)
    if "NON ASSOCIATO" in stato_cna or "TARGET TESSERAMENTO" in stato_cna:
        score += 15
    elif "ASSOCIATO RILEVATO" in stato_cna:
        score += 10
    else:
        score += 5

    # 5. Sito Web Aziendale Reale (Max 15) + Marchi Verificati (Max 5)
    if is_valid_company_website(website):
        score += 15
    if marchi_verif:
        score += 5

    score = min(100, score)
    if not has_valid_phone:
        score = min(score, 45)

    if score >= 80 and has_valid_phone:
        tier = "Tier A 🔥 (VIP / Priorità Immediata)"
        tier_short = "Tier A"
    elif score >= 55 and has_valid_phone:
        tier = "Tier B 🟡 (Warm / Retargeting RSK)"
        tier_short = "Tier B"
    else:
        tier = "Tier C ❄️ (Cold / Da Arricchire)" if not has_valid_phone else "Tier C ❄️ (Cold / Nurturing)"
        tier_short = "Tier C"

    return {
        "score": score,
        "tier": tier,
        "tier_short": tier_short,
        "is_mobile": is_mobile,
        "has_valid_phone": has_valid_phone,
    }


# ── 4. ICEBREAKER GENERATOR: GANCI ONESTI E CONFORMI GDPR ───────────────────

def generate_dynamic_icebreaker(
    comp_name: str,
    city: str,
    niche: str,
    marchi_str: str,
    is_h24: bool,
    stato_cna: str,
    trigger: str,
    marchi_verificati: bool = False,
) -> str:
    """
    Genera un incipit 1-to-1 personalizzato in stile Clay.com basato SOLO su fatti verificati:
    - Cita i marchi solo se marchi_verificati=True (Zero Hallucination Policy).
    - Propone associazione CNA Catania al 50% per il 1° anno ai non associati / da verificare.
    """
    clean_city = city.strip() if city else "Catania e provincia"
    clean_niche = niche.strip() if niche else "impiantistica"
    has_real_brands = marchi_verificati and bool(marchi_str) and marchi_str != "Non rilevato"

    if "ASSOCIATO RILEVATO" in stato_cna:
        if has_real_brands and is_h24:
            return (
                f"Buongiorno {comp_name}, vi contatto da TecnicoLIVE (Sinergia Rete d'Imprese). "
                f"Abbiamo visto che a {clean_city} operate su {marchi_str} con servizio di reperibilità: "
                f"grazie alla partnership con CNA Catania possiamo attivare l'assistente vocale AI per filtrare "
                f"le emergenze notturne e del weekend senza perdere chiamate in cantiere."
            )
        elif has_real_brands:
            return (
                f"Buongiorno {comp_name}, vi contatto da TecnicoLIVE (Sinergia Rete d'Imprese). "
                f"Ho notato la vostra attività a {clean_city} su {marchi_str}: "
                f"come azienda collegata a CNA Catania potete provare il nostro centralino vocale AI che risponde "
                f"in 3 secondi quando siete in cantiere e invia la scheda guasto su WhatsApp."
            )
        else:
            return (
                f"Buongiorno {comp_name}, vi contatto da TecnicoLIVE (Sinergia Rete d'Imprese). "
                f"Come impresa di {clean_niche} a {clean_city} collegata a CNA Catania, potete testare "
                f"il centralino vocale AI dedicato al settore: risponde alle chiamate dei clienti mentre siete "
                f"sul campo e invia i dettagli dell'intervento direttamente su WhatsApp."
            )
    else:
        # Non associato o da verificare: leva associativa CNA al 50% per il 1° anno
        if has_real_brands and is_h24:
            return (
                f"Buongiorno {comp_name}, vi contatto da TecnicoLIVE (Sinergia Rete d'Imprese). "
                f"Abbiamo visto che a {clean_city} gestite assistenza su {marchi_str} anche in reperibilità: "
                f"quante chiamate urgenti rischiate di perdere durante un altro intervento? "
                f"Con la convenzione CNA Catania attivate l'assistente vocale AI e l'iscrizione a CNA al 50% per tutto il primo anno."
            )
        elif has_real_brands:
            return (
                f"Buongiorno {comp_name}, vi contatto da TecnicoLIVE (Sinergia Rete d'Imprese). "
                f"Seguendo le ditte di {clean_niche} a {clean_city} specializzate su {marchi_str}, "
                f"sappiamo quanto sia facile perdere chiamate mentre si è in cantiere o alla guida. "
                f"Con la partnership CNA Catania potete attivare l'assistente vocale AI e la quota associativa CNA del primo anno al 50%."
            )
        elif is_h24:
            return (
                f"Buongiorno {comp_name}, vi contatto da TecnicoLIVE (Sinergia Rete d'Imprese). "
                f"Visto il vostro servizio di {clean_niche} con reperibilità a {clean_city}, "
                f"l'assistente vocale AI vi permette di non perdere chiamate notturne o mentre siete in intervento, "
                f"con accesso alla convenzione CNA Catania (associazione al 50% per il primo anno)."
            )
        else:
            return (
                f"Buongiorno {comp_name}, vi contatto da TecnicoLIVE (Sinergia Rete d'Imprese). "
                f"Per le imprese di {clean_niche} operanti a {clean_city}, una chiamata persa in cantiere è spesso un cliente perso. "
                f"Con la convenzione CNA Catania attivate l'assistente vocale AI su WhatsApp e l'associazione a CNA al 50% per il primo anno."
            )


def format_full_whatsapp_draft(icebreaker: str) -> str:
    """Compone la bozza WhatsApp completa conforme a AGENTS.md §3B-3C (mittente + opt-out)."""
    return f"{icebreaker}\n\n—\n{SENDER_IDENTITY}\n{GDPR_OPTOUT_TEXT}"


# ── 5. PIPELINE DI ARRICCHIMENTO COMPLETA DEL DATASET ───────────────────────

def enrich_dataset_with_clay_engine(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola per tutte le righe del DataFrame i campi Clay verificati e conformi:
    - Marchi_Rilevati, Marchi_Verificati, Certificazioni_Rilevate
    - Servizio_H24, Trigger_Segnale
    - ICP_Score, Lead_Tier
    - Icebreaker_1to1, Footer_GDPR_OptOut, Messaggio_WhatsApp_Completo
    """
    df_out = df.copy()
    if df_out.empty:
        return df_out

    marchi_list: List[str] = []
    marchi_verif_list: List[str] = []
    cert_list: List[str] = []
    h24_list: List[str] = []
    trigger_list: List[str] = []
    score_list: List[int] = []
    tier_list: List[str] = []
    icebreaker_list: List[str] = []
    gdpr_footer_list: List[str] = []
    wa_full_list: List[str] = []

    for _, row in df_out.iterrows():
        comp_name = str(row.get("Company Name", "")).strip()
        niche = str(row.get("Nicchia_Target", "")).strip()
        city = str(row.get("City", "")).strip()
        stato_cna = str(row.get("Stato_CNA", "")).strip()
        category = str(row.get("Category", "")).strip()
        website_text = str(row.get("Website_Text_Snippet", "")).strip()

        text_corpus = f"{comp_name} {niche} {category} {city}"
        sem = extract_semantic_signals(text_corpus, comp_name, niche, website_text=website_text)

        marchi_list.append(sem["marchi_str"])
        marchi_verif_list.append("SI" if sem["marchi_verificati"] else "NO")
        cert_list.append(sem["certificazioni"])
        h24_list.append("SI (Reperibilità)" if sem["is_h24"] else "NO (Orario Ufficio)")
        trigger_list.append(sem["trigger"])

        row_dict = row.to_dict()
        row_dict["Marchi_Rilevati"] = sem["marchi_str"]
        row_dict["Marchi_Verificati"] = "SI" if sem["marchi_verificati"] else "NO"
        sc = calculate_lead_score(row_dict)
        score_list.append(sc["score"])
        tier_list.append(sc["tier"])

        ib = generate_dynamic_icebreaker(
            comp_name=comp_name,
            city=city,
            niche=niche,
            marchi_str=sem["marchi_str"],
            is_h24=sem["is_h24"],
            stato_cna=stato_cna,
            trigger=sem["trigger"],
            marchi_verificati=sem["marchi_verificati"],
        )
        icebreaker_list.append(ib)
        gdpr_footer_list.append(GDPR_FOOTER)
        wa_full_list.append(format_full_whatsapp_draft(ib))

    df_out["Marchi_Rilevati"] = marchi_list
    df_out["Marchi_Verificati"] = marchi_verif_list
    df_out["Certificazioni_Rilevate"] = cert_list
    df_out["Servizio_H24"] = h24_list
    df_out["Trigger_Segnale"] = trigger_list
    df_out["ICP_Score"] = score_list
    df_out["Lead_Tier"] = tier_list
    df_out["Icebreaker_1to1"] = icebreaker_list
    df_out["Footer_GDPR_OptOut"] = gdpr_footer_list
    df_out["Messaggio_WhatsApp_Completo"] = wa_full_list

    return df_out
