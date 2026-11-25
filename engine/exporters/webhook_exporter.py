"""
webhook_exporter.py — Esportazione CSV/XLSX canonica IT/EU e consegna Webhook verso RSK System / GHL / n8n / Make.

Sicurezza & Human-in-the-Loop (AGENTS.md §1):
- Esclude categoricamente i lead con LIA status == 'BLOCKED' o presenti in suppression_list.
- Non inserisce MAI indirizzi PEC nel campo 'email' destinato all'outreach.
- Default dry_run=True: salva i payload JSON in produzione/01_bozze_outbound/ per revisione umana.
  L'invio HTTP reale avviene solo se dry_run=False E human_approved=True E webhook_url è fornito.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import pandas as pd

from engine.compliance.lia_engine import is_pec_email
from engine.schemas.lead import LeadRecord
from src.config import GDPR_OPTOUT_TEXT, ROOT_DIR, SENDER_IDENTITY

DEFAULT_DRAFT_DIR = ROOT_DIR / "produzione" / "01_bozze_outbound"


def leads_to_dataframe(leads: List[LeadRecord]) -> pd.DataFrame:
    """Appiattisce i LeadRecord nello schema tabellare canonico IT/EU stile Clay."""
    rows: List[Dict[str, Any]] = []
    for ld in leads:
        safe_email = "" if is_pec_email(ld.email) else ld.email
        rows.append(
            {
                "Company_Name": ld.company_name,
                "Partita_IVA": ld.vat_id,
                "Codice_Fiscale": ld.tax_code,
                "VIES_Valid": "" if ld.registry.vies_valid is None else ("SI" if ld.registry.vies_valid else "NO"),
                "ATECO_Code": ld.registry.ateco_code,
                "Forma_Giuridica": ld.registry.forma_giuridica,
                "REA": ld.registry.rea_code,
                "Stato_Attivita": ld.registry.activity_status,
                "SDI_Code": ld.registry.sdi_code,
                "PEC_Solo_Registro": ld.pec,
                "Country": ld.country_code,
                "Province": ld.province,
                "City": ld.city,
                "ISTAT_Code": ld.istat_code,
                "Postal_Code": ld.postal_code,
                "Address": ld.address,
                "Phone_E164": ld.phone_e164,
                "Phone_Type": ld.phone_type,
                "Email_Aziendale": safe_email,
                "Email_MX_Valid": "" if ld.email_mx_valid is None else ("SI" if ld.email_mx_valid else "NO"),
                "Website": ld.website,
                "HTTP_Status": ld.tech_audit.http_status,
                "Has_SSL": "SI" if ld.tech_audit.has_ssl else "NO",
                "CMS_Stack": ld.tech_audit.cms_stack,
                "Tracking_Pixels": ", ".join(ld.tech_audit.tracking_pixels),
                "Has_WhatsApp_CTA": "SI" if ld.tech_audit.has_whatsapp_cta else "NO",
                "Has_Booking_Form": "SI" if ld.tech_audit.has_booking_or_quote_form else "NO",
                "Business_Model": ld.ai_qualification.business_model,
                "ICP_Score": ld.ai_qualification.icp_fit_score,
                "Lead_Tier": ld.ai_qualification.lead_tier,
                "Recommended_Product": ld.ai_qualification.recommended_product,
                "Recommended_Product_URL": ld.ai_qualification.recommended_product_url,
                "AI_Pain_Points": " | ".join(ld.ai_qualification.detected_pain_points),
                "Outreach_Angle": ld.ai_qualification.outreach_angle,
                "Icebreaker_1to1": ld.ai_qualification.icebreaker_1to1,
                "LIA_Status": ld.lia.status if ld.lia else "NOT_ASSESSED",
                "PEC_Blocked": "SI" if (ld.lia and ld.lia.pec_cold_outreach_blocked) else "NO",
                "RPO_Check_Required": "SI" if (ld.lia and ld.lia.rpo_check_required) else "NO",
                "GDPR_OptOut": GDPR_OPTOUT_TEXT,
                "Enrichment_Cost_EUR": ld.enrichment_cost_eur,
            }
        )
    return pd.DataFrame(rows)


def export_leads_to_csv(leads: List[LeadRecord], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = leads_to_dataframe(leads)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def build_webhook_payload(
    campaign_id: str,
    leads: List[LeadRecord],
) -> Dict[str, Any]:
    """
    Costruisce il payload JSON pronto per RSK System / GoHighLevel / n8n / Make.
    Scarta qualsiasi lead BLOCKED o privo di valutazione LIA valida, e garantisce zero PEC in 'email'.
    """
    eligible: List[Dict[str, Any]] = []
    skipped_blocked = 0

    for ld in leads:
        if ld.lia and (ld.lia.status == "BLOCKED" or ld.lia.suppressed):
            skipped_blocked += 1
            continue
        safe_email = "" if is_pec_email(ld.email) else ld.email
        if not (ld.phone_e164 or safe_email):
            skipped_blocked += 1
            continue

        eligible.append(
            {
                "company_name": ld.company_name,
                "vat_id": ld.vat_id,
                "country": ld.country_code,
                "province": ld.province,
                "city": ld.city,
                "postal_code": ld.postal_code,
                "address": ld.address,
                "phone": ld.phone_e164,
                "email": safe_email,
                "website": ld.website,
                "tags": [
                    f"Target: {ld.niche or ld.category or 'PMI'}",
                    f"Upsell: {ld.ai_qualification.recommended_product}",
                    f"Tier: {ld.ai_qualification.lead_tier.split()[0]}",
                    f"LIA: {ld.lia.status if ld.lia else 'PENDING'}",
                ],
                "custom_fields": {
                    "ateco_code": ld.registry.ateco_code,
                    "vies_valid": ld.registry.vies_valid,
                    "cms_stack": ld.tech_audit.cms_stack,
                    "recommended_product": ld.ai_qualification.recommended_product,
                    "recommended_product_url": ld.ai_qualification.recommended_product_url,
                    "outreach_angle": ld.ai_qualification.outreach_angle,
                    "icebreaker_1to1": ld.ai_qualification.icebreaker_1to1,
                    "rpo_check_required": ld.lia.rpo_check_required if ld.lia else False,
                    "gdpr_sender": SENDER_IDENTITY,
                    "gdpr_optout": GDPR_OPTOUT_TEXT,
                },
            }
        )

    return {
        "campaign_id": campaign_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "human_in_the_loop_required": True,
        "eligible_count": len(eligible),
        "skipped_blocked_count": skipped_blocked,
        "contacts": eligible,
    }


async def dispatch_webhook(
    campaign_id: str,
    leads: List[LeadRecord],
    webhook_url: Optional[str] = None,
    dry_run: bool = True,
    human_approved: bool = False,
    draft_dir: Path = DEFAULT_DRAFT_DIR,
) -> Dict[str, Any]:
    """
    Salva sempre la bozza JSON per approvazione umana.
    Invia HTTP POST solo quando dry_run=False E human_approved=True E webhook_url è valorizzato.
    """
    payload = build_webhook_payload(campaign_id, leads)
    draft_dir.mkdir(parents=True, exist_ok=True)
    draft_path = draft_dir / f"webhook_draft_{campaign_id}.json"
    draft_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if dry_run or not human_approved:
        return {
            "status": "DRAFT_SAVED_FOR_HUMAN_REVIEW",
            "draft_path": str(draft_path),
            "eligible_count": payload["eligible_count"],
            "skipped_blocked_count": payload["skipped_blocked_count"],
            "dispatched": False,
        }

    if not webhook_url:
        return {
            "status": "NO_WEBHOOK_URL",
            "draft_path": str(draft_path),
            "dispatched": False,
        }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            return {
                "status": "DISPATCHED" if resp.status < 300 else f"HTTP_{resp.status}",
                "http_status": resp.status,
                "draft_path": str(draft_path),
                "eligible_count": payload["eligible_count"],
                "dispatched": resp.status < 300,
            }
