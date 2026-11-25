"""
swot_analyzer.py — Motore deterministico di analisi pre-chiamata:
Estrae Pain Points attaccabili, Weak Points, Strengths e Brief "Cosa Vendere e Perché"
basandosi esclusivamente su segnali reali osservati (Zero Hallucination Policy, AGENTS.md §2).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from engine.schemas.campaign import UpsellProduct
from engine.schemas.lead import LeadSignalItem, PreCallSalesBrief

_CAPITAL_COMPANY_RE = re.compile(r"\b(s\.?r\.?l\.?s?|s\.?p\.?a\.?|s\.?r\.?l\.?\s+unipersonale)\b", re.IGNORECASE)
_PARTNERSHIP_RE = re.compile(r"\b(s\.?a\.?s\.?|s\.?n\.?c\.?)\b", re.IGNORECASE)


def infer_company_size_profile(
    company_name: str,
    forma_giuridica: str = "",
    employees_count: Optional[int] = None,
    revenue_eur: Optional[float] = None,
) -> Dict[str, Any]:
    """Classifica la dimensione aziendale esclusivamente da dati camerali o forma giuridica reale."""
    if employees_count is not None and employees_count >= 10:
        return {
            "label": f"Strutturata ({employees_count} dipendenti)",
            "tier": "structured",
            "is_structured": True,
        }
    if employees_count is not None and employees_count >= 4:
        return {
            "label": f"Piccola Impresa ({employees_count} dipendenti)",
            "tier": "small_team",
            "is_structured": True,
        }
    if employees_count is not None and employees_count >= 1:
        return {
            "label": f"Microimpresa ({employees_count} dip.)",
            "tier": "micro",
            "is_structured": False,
        }
    if revenue_eur is not None and revenue_eur >= 500_000:
        return {
            "label": f"Strutturata (Fatt. ~{int(revenue_eur / 1000)}k€)",
            "tier": "structured",
            "is_structured": True,
        }

    fg_or_name = f"{forma_giuridica} {company_name}".strip()
    if _CAPITAL_COMPANY_RE.search(fg_or_name):
        return {
            "label": "Società di Capitali (S.r.l. / S.p.A.)",
            "tier": "small_team",
            "is_structured": True,
        }
    if _PARTNERSHIP_RE.search(fg_or_name):
        return {
            "label": "Società di Persone (S.n.c. / S.a.s.)",
            "tier": "small_team",
            "is_structured": False,
        }
    return {
        "label": "Ditta Individuale / Artigiano",
        "tier": "micro",
        "is_structured": False,
    }


def analyze_lead_swot_and_brief(
    *,
    company_name: str,
    city: str = "",
    niche: str = "",
    category: str = "",
    phone_e164: str = "",
    phone_type: str = "Unknown",
    email: str = "",
    email_mx_valid: Optional[bool] = None,
    pec: str = "",
    website: str = "",
    has_valid_piva: bool = False,
    vies_valid: Optional[bool] = None,
    cna_status: str = "",
    brands: Optional[List[str]] = None,
    certifications: Optional[List[str]] = None,
    is_h24: bool = False,
    http_status: int = 0,
    has_ssl: bool = False,
    cms_stack: str = "Unknown",
    tracking_pixels: Optional[List[str]] = None,
    has_whatsapp_cta: bool = False,
    has_booking_or_quote_form: bool = False,
    social_links: Optional[Dict[str, str]] = None,
    employees_count: Optional[int] = None,
    revenue_eur: Optional[float] = None,
    forma_giuridica: str = "",
    recommended_product: UpsellProduct = "rsksystem",
    recommended_product_name: str = "RSK System",
) -> Dict[str, Any]:
    """
    Costruisce in modo deterministico (Zero Hallucination) i record pre-chiamata:
    - pain_signals: Pain point commerciali/operativi da attaccare
    - weak_points: Punti deboli digitali/anagrafici osservati
    - strengths: Punti di forza reali dell'azienda
    - sales_brief: Cosa vendere e perché prima di chiamare
    """
    brands_list = [b for b in (brands or []) if b and b.lower() != "non rilevato"]
    certs_list = [c for c in (certifications or []) if c and c.lower() != "non rilevate"]
    pixels_list = [p for p in (tracking_pixels or []) if p]
    socials = social_links or {}
    city_lbl = city.strip() or "zona locale"
    niche_lbl = niche.strip() or category.strip() or "settore operativo"

    size_info = infer_company_size_profile(
        company_name=company_name,
        forma_giuridica=forma_giuridica,
        employees_count=employees_count,
        revenue_eur=revenue_eur,
    )
    has_live_site = bool(website) and (http_status == 200 or cms_stack != "Unknown" or has_ssl or bool(pixels_list))
    has_ads_pixels = any(
        p in pixels_list
        for p in ("Meta Pixel", "Google Tag Manager", "Google Analytics 4", "TikTok Pixel", "LinkedIn Insight Tag")
    )

    pain_signals: List[LeadSignalItem] = []
    weak_points: List[LeadSignalItem] = []
    strengths: List[LeadSignalItem] = []

    # ── 1. STRENGTHS (Punti di Forza Reali) ─────────────────────────────────
    if has_ads_pixels:
        pixels_str = ", ".join(pixels_list)
        strengths.append(
            LeadSignalItem(
                id="str_ads_active",
                kind="strength",
                category="Marketing & Tech",
                title="Investe già in Ads / Tracciamento",
                description=f"Rilevati script di tracciamento ({pixels_str}): azienda già abituata a investire sul digitale.",
                severity="high",
                icon="megaphone",
                color="emerald",
                evidence=f"Pixel/Tag rilevati sul sito: {pixels_str}",
            )
        )

    if brands_list:
        brands_str = ", ".join(brands_list[:5])
        strengths.append(
            LeadSignalItem(
                id="str_brands",
                kind="strength",
                category="Posizionamento",
                title=f"Specializzazione su Marchi Noti ({len(brands_list)})",
                description=f"Opera su brand riconosciuti ({brands_str}), indice di clientela fidelizzata e ticket medio solido.",
                severity="high",
                icon="award",
                color="emerald",
                evidence=f"Marchi rilevati: {brands_str}",
            )
        )

    if certs_list:
        certs_str = ", ".join(certs_list)
        strengths.append(
            LeadSignalItem(
                id="str_certs",
                kind="strength",
                category="Normativo",
                title="Abilitazioni & Certificazioni Attive",
                description=f"Possiede certificazioni tecniche rilevate ({certs_str}): alta affidabilità normativa.",
                severity="medium",
                icon="shield-check",
                color="emerald",
                evidence=f"Certificazioni: {certs_str}",
            )
        )

    if is_h24:
        strengths.append(
            LeadSignalItem(
                id="str_h24",
                kind="strength",
                category="Servizio",
                title="Servizio Reperibilità / Urgenze H24",
                description="Offre pronto intervento: intercetta richieste ad alta urgenza e marginalità elevata.",
                severity="high",
                icon="clock",
                color="emerald",
                evidence="Keyword H24 / Pronto Intervento rilevate nei testi aziendali",
            )
        )

    if phone_type == "Mobile" and phone_e164:
        strengths.append(
            LeadSignalItem(
                id="str_mobile",
                kind="strength",
                category="Contatto",
                title="Cellulare Diretto E.164 Disponibile",
                description="Numero mobile diretto verificato: accesso rapido al titolare o responsabile operativo.",
                severity="medium",
                icon="smartphone",
                color="emerald",
                evidence=f"Telefono mobile: {phone_e164}",
            )
        )

    if size_info["is_structured"]:
        strengths.append(
            LeadSignalItem(
                id="str_structured",
                kind="strength",
                category="Dimensione",
                title=size_info["label"],
                description="Struttura organizzata con capacità di spesa B2B per soluzioni ricorrenti o multi-utente.",
                severity="medium",
                icon="building-2",
                color="emerald",
                evidence=f"Profilo dimensionale: {size_info['label']}",
            )
        )

    if has_valid_piva:
        strengths.append(
            LeadSignalItem(
                id="str_piva",
                kind="strength",
                category="Fiscale",
                title="Partita IVA Validata (Luhn OK)" + (" · VIES Attiva" if vies_valid else ""),
                description="Impresa fiscalmente verificata e idonea a fatturazione B2B e convenzioni.",
                severity="low",
                icon="badge-check",
                color="emerald",
                evidence="Verifica formale P.IVA superata",
            )
        )

    if has_live_site and has_ssl:
        cms_note = f" su {cms_stack}" if cms_stack and cms_stack != "Unknown" else ""
        strengths.append(
            LeadSignalItem(
                id="str_ssl_site",
                kind="strength",
                category="Digitale",
                title=f"Sito Web Sicuro HTTPS{cms_note}",
                description=f"Presenza web proprietaria attiva con certificato SSL{cms_note}.",
                severity="low",
                icon="globe",
                color="emerald",
                evidence=f"Sito: {website}",
            )
        )

    is_cna_non_assoc = "NON ASSOCIATO" in (cna_status or "").upper()
    if recommended_product == "tecnicolive" and is_cna_non_assoc:
        strengths.append(
            LeadSignalItem(
                id="str_cna_50",
                kind="strength",
                category="Convenzione",
                title="Eligibile Sconto 50% CNA Catania",
                description="Non ancora associato: può accedere alla quota associativa CNA al 50% per il 1° anno.",
                severity="high",
                icon="ticket",
                color="blue",
                evidence=f"Stato CNA: {cna_status}",
            )
        )

    # ── 2. WEAK POINTS (Punti Deboli Osservati) ─────────────────────────────
    if not website:
        weak_points.append(
            LeadSignalItem(
                id="weak_no_site",
                kind="weak",
                category="Digitale",
                title="Assenza Sito Web Proprietario",
                description="Nessun sito aziendale rilevato: dipende solo da passaparola, portali o scheda Maps.",
                severity="high",
                icon="globe-off",
                color="amber",
                evidence="Campo Website assente o non aziendale",
            )
        )
    else:
        if has_live_site and not has_ssl:
            weak_points.append(
                LeadSignalItem(
                    id="weak_no_ssl",
                    kind="weak",
                    category="Digitale",
                    title="Sito privo di HTTPS/SSL",
                    description="Il browser segnala il sito come 'Non Sicuro', riducendo la fiducia dei nuovi clienti.",
                    severity="medium",
                    icon="shield-alert",
                    color="amber",
                    evidence=f"URL senza SSL attivo: {website}",
                )
            )
        if has_live_site and not pixels_list:
            weak_points.append(
                LeadSignalItem(
                    id="weak_no_pixels",
                    kind="weak",
                    category="Marketing & Tech",
                    title="Nessun Pixel / Analytics Rilevato",
                    description="Non traccia le visite sul sito né può fare retargeting su chi cerca un preventivo.",
                    severity="medium",
                    icon="radar",
                    color="amber",
                    evidence="Audit HTML: 0 pixel (Meta, GTM, GA4) rilevati",
                )
            )
        if has_live_site and not has_whatsapp_cta:
            weak_points.append(
                LeadSignalItem(
                    id="weak_no_wa",
                    kind="weak",
                    category="Conversione",
                    title="Manca Pulsante Rapido WhatsApp",
                    description="I visitatori da smartphone non possono scrivere su WhatsApp con un clic.",
                    severity="medium",
                    icon="message-circle-off",
                    color="amber",
                    evidence="Audit HTML: nessun link wa.me / api.whatsapp.com",
                )
            )
        if has_live_site and not has_booking_or_quote_form:
            weak_points.append(
                LeadSignalItem(
                    id="weak_no_form",
                    kind="weak",
                    category="Conversione",
                    title="Assenza Modulo Preventivo / Booking",
                    description="Nessun flusso guidato sul sito per raccogliere richieste o appuntamenti.",
                    severity="medium",
                    icon="calendar-x",
                    color="amber",
                    evidence="Audit HTML: nessun form prenotazione o richiesta preventivo",
                )
            )

    if not phone_e164:
        weak_points.append(
            LeadSignalItem(
                id="weak_no_phone",
                kind="weak",
                category="Contatto",
                title="Telefono E.164 Assente",
                description="Contatto telefonico mancante o non valido: richiede arricchimento prima della chiamata.",
                severity="high",
                icon="phone-off",
                color="amber",
                evidence="Nessun numero E.164 valido",
            )
        )
    elif phone_type == "Fisso":
        weak_points.append(
            LeadSignalItem(
                id="weak_landline_only",
                kind="weak",
                category="Contatto",
                title="Solo Telefono Fisso (No Cellulare)",
                description="Numero fisso aziendale: rischio segreteria, linee occupate o nessuno in ufficio durante i cantieri.",
                severity="medium",
                icon="phone",
                color="amber",
                evidence=f"Telefono rilevato di tipo Fisso: {phone_e164}",
            )
        )

    if not email:
        weak_points.append(
            LeadSignalItem(
                id="weak_no_email",
                kind="weak",
                category="Contatto",
                title="Email Outbound Assente" + (" (Solo PEC)" if pec else ""),
                description="Nessuna email ordinaria pubblica: impossibile inviare preventivi/demo via email (PEC bloccata GDPR).",
                severity="low",
                icon="mail-x",
                color="amber",
                evidence=f"PEC rilevata: {pec}" if pec else "Nessuna email non-PEC trovata",
            )
        )
    elif email_mx_valid is False:
        weak_points.append(
            LeadSignalItem(
                id="weak_bad_mx",
                kind="weak",
                category="Contatto",
                title="Record MX Email Non Valido",
                description="Il dominio email non ha record MX validi: alto rischio bounce.",
                severity="medium",
                icon="mail-warning",
                color="amber",
                evidence=f"MX check fallito su {email}",
            )
        )

    if not has_valid_piva:
        weak_points.append(
            LeadSignalItem(
                id="weak_no_piva",
                kind="weak",
                category="Fiscale",
                title="Partita IVA Non Rilevata",
                description="P.IVA mancante nel record: da verificare prima dell'emissione di offerte formali.",
                severity="low",
                icon="file-warning",
                color="amber",
                evidence="Campo Partita_IVA vuoto o non validato",
            )
        )

    # ── 3. PAIN POINTS DA ATTACCARE (Leve di Vendita Dirette) ───────────────
    if has_ads_pixels and (not has_whatsapp_cta or not has_booking_or_quote_form or recommended_product == "tecnicolive"):
        pixels_str = ", ".join(pixels_list)
        pain_signals.append(
            LeadSignalItem(
                id="pain_ads_leak",
                kind="pain",
                category="ROI Marketing",
                title="Budget Ads a Rischio Dispersione",
                description=(
                    f"Usa già tracciamenti ({pixels_str}) per portare clienti, ma senza risposta vocale immediata H24 "
                    f"o CTA WhatsApp/Preventivo rischia di sprecare i lead pagati in pubblicità."
                ),
                severity="high",
                icon="flame",
                color="red",
                evidence=f"Tech Stack: {pixels_str} | WA CTA: {'Sì' if has_whatsapp_cta else 'No'}",
                attack_angle="Attacca sul ROI delle sponsorizzate: 'State già pagando per farvi trovare, ma se squilla mentre siete occupati il lead chiama il concorrente.'",
            )
        )

    if recommended_product == "tecnicolive":
        if is_h24:
            pain_signals.append(
                LeadSignalItem(
                    id="pain_h24_missed",
                    kind="pain",
                    category="Operativo H24",
                    title="Emergenze H24 & Chiamate Simultanee",
                    description="Offrendo pronto intervento, quando il tecnico è già al telefono o in riparazione la seconda chiamata urgentissima trova occupato.",
                    severity="high",
                    icon="phone-missed",
                    color="red",
                    evidence="Segnale H24 / Pronto Intervento attivo",
                    attack_angle="Proponi TecnicoLIVE per risposte simultanee illimitate H24 con scheda guasto immediata su WhatsApp.",
                )
            )
        elif size_info["is_structured"]:
            pain_signals.append(
                LeadSignalItem(
                    id="pain_team_bottleneck",
                    kind="pain",
                    category="Organizzazione",
                    title="Collo di Bottiglia su Più Squadre / Tecnici",
                    description=f"Profilo {size_info['label']}: gestire picchi di telefonate per più furgoni o cantieri satura il centralino o il titolare.",
                    severity="high",
                    icon="users",
                    color="red",
                    evidence=f"Dimensione rilevata: {size_info['label']}",
                    attack_angle="Proponi Piano Pro/Business TecnicoLIVE per pre-diagnosi automatica e smistamento interventi.",
                )
            )
        else:
            pain_signals.append(
                LeadSignalItem(
                    id="pain_field_missed",
                    kind="pain",
                    category="Operativo",
                    title="Chiamate Perse in Cantiere / Alla Guida",
                    description=f"Nel settore {niche_lbl} a {city_lbl}, chi risponde mentre è sotto una caldaia o sul furgone perde nuovi clienti al primo squillo a vuoto.",
                    severity="high",
                    icon="wrench",
                    color="red",
                    evidence=f"Nicchia: {niche_lbl} | Profilo: {size_info['label']}",
                    attack_angle="Attacca sul costo di un singolo lavoro perso vs canone TecnicoLIVE (con CNA Catania 50% 1° anno).",
                )
            )

        if certs_list or any(k in niche_lbl.lower() for k in ("calda", "termo", "clima", "hvac", "idraul")):
            pain_signals.append(
                LeadSignalItem(
                    id="pain_citel_seasonal",
                    kind="pain",
                    category="Normativo & Stagionale",
                    title="Picchi Stagionali & Adempimenti CITEL/F-Gas",
                    description="Picchi acuti estate/inverno e raccolta dati per Bollino Blu / CITEL / F-Gas sottraggono tempo produttivo ai tecnici.",
                    severity="medium",
                    icon="thermometer",
                    color="red",
                    evidence=f"Settore {niche_lbl}" + (f" | Certificazioni: {', '.join(certs_list)}" if certs_list else ""),
                    attack_angle="Evidenzia che l'assistente vocale raccoglie già marca, modello e tipo guasto prima della richiamata.",
                )
            )
    elif recommended_product == "monetizelab":
        pain_signals.append(
            LeadSignalItem(
                id="pain_agency_scale",
                kind="pain",
                category="Acquisizione Clienti",
                title="Dipendenza da Outreach Manuale & Margini Ricorrenti",
                description="Agenzie e creator faticano a trasformare la lead generation locale in pacchetti ricorrenti scalabili.",
                severity="high",
                icon="trending-up",
                color="red",
                evidence=f"Settore rilevato: {niche_lbl}",
                attack_angle="Proponi MonetizeLab per automatizzare discovery locale e monetizzazione ricorrente.",
            )
        )
    else:
        pain_signals.append(
            LeadSignalItem(
                id="pain_crm_followup",
                kind="pain",
                category="Follow-up Lead",
                title="Dispersione Richieste & Mancato Follow-up",
                description=f"Senza CRM con Smart Lists WhatsApp/Email automatiche, i contatti locali di {niche_lbl} raffreddano prima del preventivo.",
                severity="high",
                icon="layers",
                color="red",
                evidence=f"Settore: {niche_lbl} | WA CTA: {'Sì' if has_whatsapp_cta else 'No'}",
                attack_angle="Proponi RSK System per centralizzare i lead e automatizzare i follow-up WhatsApp/Email.",
            )
        )

    if has_live_site and (not has_whatsapp_cta or not has_booking_or_quote_form):
        pain_signals.append(
            LeadSignalItem(
                id="pain_site_conversion",
                kind="pain",
                category="Conversione Web",
                title="Sito Vetrina che Non Converte Visitatori",
                description="Il sito è attivo ma manca di cattura immediata (WhatsApp o form preventivo): i clienti escono e cercano altrove.",
                severity="medium",
                icon="mouse-pointer-click",
                color="red",
                evidence=f"Sito: {website} | WA: {has_whatsapp_cta} | Form: {has_booking_or_quote_form}",
                attack_angle="Usa il gap digitale rilevato sul loro sito reale come gancio concreto in chiamata.",
            )
        )

    # ── 4. BRIEF PRE-CHIAMATA ("COSA VENDERE E PERCHÉ") ─────────────────────
    if recommended_product == "tecnicolive":
        if size_info["tier"] == "structured":
            plan = "TecnicoLIVE Business (369€/m) o Pro (269€/m) · -20% annuale"
        elif is_h24 or has_ads_pixels:
            plan = "TecnicoLIVE Pro (269€/m) · Chiamate simultanee + Pre-diagnosi"
        else:
            plan = "TecnicoLIVE Base (169€/m) · -20% annuale + CNA Catania 50% 1° anno"
    elif recommended_product == "monetizelab":
        plan = "MonetizeLab Agency / Creator Suite"
    else:
        plan = "RSK System CRM + Smart Lists WhatsApp/Email"

    primary_pain = pain_signals[0] if pain_signals else None
    top_strength = strengths[0] if strengths else None

    why_parts: List[str] = [f"Azienda classificata come **{size_info['label']}** nel settore **{niche_lbl}** ({city_lbl})."]
    if has_ads_pixels:
        why_parts.append(f"Ha già {', '.join(pixels_list)} attivo sul sito (investe in visibilità), quindi ogni chiamata o contatto perso ha un costo reale diretto.")
    elif is_h24:
        why_parts.append("Offre reperibilità H24: le chiamate di emergenza hanno alto valore e non possono andare in segreteria.")
    elif not website:
        why_parts.append("Non ha un sito web proprietario: dipende dal contatto telefonico diretto e dal passaparola.")
    if recommended_product == "tecnicolive" and is_cna_non_assoc:
        why_parts.append("Non risulta ancora associata CNA: la leva **CNA Catania al 50% per il 1° anno** abbatte la barriera d'ingresso.")

    if phone_type == "Fisso":
        expected_obj = "«Risponde già la segretaria in ufficio» -> Risposta: chiamate simultanee illimitate quando la linea è occupata + copertura serale/weekend."
    elif has_ads_pixels:
        expected_obj = "«Abbiamo già chi ci segue sito/pubblicità» -> Risposta: non tocchiamo le ads, potenziamo la conversione telefonica/WhatsApp dei lead che già pagate."
    elif not size_info["is_structured"]:
        expected_obj = "«I clienti vogliono parlare solo con me» -> Risposta: l'AI risponde in 3s, raccoglie guasto e indirizzo e glieli manda su WhatsApp per richiamare preparato."
    else:
        expected_obj = "«Costa troppo / non abbiamo tempo per configurarlo» -> Risposta: recupero di 1-2 interventi al mese copre il canone; setup guidato."

    tech_maturity = "Avanzata (Ads/Pixel)" if has_ads_pixels else ("Intermedia (Sito SSL)" if has_live_site and has_ssl else ("Base (Sito senza SSL)" if has_live_site else "Assente (No Sito)"))

    sales_brief = PreCallSalesBrief(
        product_key=recommended_product,
        product_name=recommended_product_name,
        recommended_plan=plan,
        company_size_label=size_info["label"],
        tech_maturity_label=tech_maturity,
        why_sell=" ".join(why_parts),
        primary_pain_to_attack=(
            f"{primary_pain.title}: {primary_pain.attack_angle or primary_pain.description}"
            if primary_pain
            else "Automazione risposta e gestione richieste clienti"
        ),
        leverage_strength=(
            f"{top_strength.title} ({top_strength.evidence})"
            if top_strength
            else f"Attività locale consolidata a {city_lbl}"
        ),
        suggested_opener=(
            f"Complimentarsi per {top_strength.title.lower()} e collegare subito: «{primary_pain.attack_angle}»"
            if top_strength and primary_pain
            else f"Apertura diretta su convenzione e recupero chiamate/contatti a {city_lbl}."
        ),
        expected_objection=expected_obj,
    )

    return {
        "company_size_label": size_info["label"],
        "tech_maturity_label": tech_maturity,
        "pain_signals": pain_signals,
        "weak_points": weak_points,
        "strengths": strengths,
        "sales_brief": sales_brief,
    }
