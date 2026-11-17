"""
massive_lead_and_content_pipeline.py
Workflow dinamico per l'elaborazione massiva di lead impiantistiche e generazione contenuti.

Architettura Staged Pipeline:
1. Tier Leggero (flash_lite / flash): Scrematura iniziale rapida e parallela di centinaia di lead (validazione P.IVA, localizzazione Catania, filtraggio spam).
2. Tier Avanzato (pro): Sintesi strategica, redazione pitch personalizzati e messaggistica outbound anti-cliché AI.
3. Fase CRM Ops: Organizzazione in segmenti target (Soci CNA vs Target Tesseramento) con rispetto rigoroso di AGENTS.md.
"""

import json
from pathlib import Path

# Definizione dello schema di output per la scrematura iniziale
SCREENING_SCHEMA = {
    "type": "object",
    "properties": {
        "company_name": {"type": "string"},
        "is_qualified": {"type": "boolean"},
        "qualification_reason": {"type": "string"},
        "target_niche": {"type": "string"},
        "cna_tier": {"type": "string", "enum": ["socio_rilevato", "target_tesseramento", "non_idoneo"]}
    },
    "required": ["company_name", "is_qualified", "qualification_reason", "target_niche", "cna_tier"]
}

# Definizione dello schema di output per la stesura avanzata del pitch
PITCH_SCHEMA = {
    "type": "object",
    "properties": {
        "company_name": {"type": "string"},
        "custom_phone_script": {"type": "string"},
        "custom_whatsapp_draft": {"type": "string"},
        "pain_point_hook": {"type": "string"}
    },
    "required": ["company_name", "custom_phone_script", "custom_whatsapp_draft", "pain_point_hook"]
}


async def run_pipeline(sample_leads):
    """
    Esegue il workflow con orchestrazione dinamica a tier differenziati.
    """
    phase("1. Scrematura Rapida Parallela (Tier Leggero: Flash-Lite)")
    log(f"Avvio scrematura iniziale su {len(sample_leads)} profili con modello flash_lite...")

    # Fan-out parallelo su modello leggero per scrematura rapida e a basso costo
    screening_agents = parallel(
        sample_leads,
        lambda lead: agent(
            prompt=(
                f"Analizza questo profilo aziendale per la campagna TecnicoLIVE - CNA Catania:\n"
                f"Nome: {lead.get('name')}\n"
                f"Comune: {lead.get('city')}\n"
                f"Settore: {lead.get('niche')}\n"
                f"P.IVA: {lead.get('piva')}\n"
                f"Telefono: {lead.get('phone')}\n\n"
                f"Determina se è qualificabile come impiantista nell'area di Catania e categorizza il cna_tier."
            ),
            schema=SCREENING_SCHEMA,
            role=f"Screener: {lead.get('name')}",
            type_name="scout",
            model="flash_lite"
        )
    )

    screened_results = await screening_agents
    qualified_leads = [res for res in screened_results if res.get("is_qualified")]
    log(f"Scrematura completata: {len(qualified_leads)} lead qualificate su {len(sample_leads)} analizzate.")

    phase("2. Stesura Pitch & Copy Strategico (Tier Avanzato: Pro)")
    log("Generazione pitch commerciale avanzato con modello pro...")

    # Stesura accurata con modello avanzato 'pro' per i lead qualificati
    pitch_agents = parallel(
        qualified_leads,
        lambda q_lead: agent(
            prompt=(
                f"Sei l'agente Creator. Redigi un pitch telefonico e una bozza WhatsApp per:\n"
                f"Azienda: {q_lead.get('company_name')}\n"
                f"Settore: {q_lead.get('target_niche')}\n"
                f"Stato CNA: {q_lead.get('cna_tier')}\n\n"
                f"Applica i principi di content-humanizer e copy-editing dal contesto .agents/product-marketing.md.\n"
                f"Se l'azienda è 'target_tesseramento', evidenzia come gancio principale la scontistica riservata sulla quota d'iscrizione del primo anno a CNA Catania oltre all'assistente vocale.\n"
                f"Evita gergo robotico AI e includi obbligatoriamente l'opzione di opt-out."
            ),
            schema=PITCH_SCHEMA,
            role=f"Pitch Creator: {q_lead.get('company_name')}",
            type_name="creator",
            model="pro"
        )
    )

    pitch_results = await pitch_agents
    log(f"Elaborazione copy completata per {len(pitch_results)} aziende.")

    phase("3. Organizzazione Segmenti CRM Ops (Human-in-the-Loop)")
    log("Preparazione liste segmentate in bozza per HubSpot/Klaviyo in attesa di approvazione umana.")

    return {
        "total_analyzed": len(sample_leads),
        "total_qualified": len(qualified_leads),
        "pitches_generated": len(pitch_results),
        "status": "ready_for_human_review"
    }
