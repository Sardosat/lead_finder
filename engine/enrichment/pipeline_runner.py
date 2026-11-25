"""
pipeline_runner.py — Orchestratore a imbuto a 3 livelli (Seed -> L1 Tech/MX/VIES -> L2 Gemini -> L3 Openapi -> LIA GDPR).
"""

import asyncio
import logging
from typing import Dict, List, Optional

import aiohttp

from engine.compliance.lia_engine import SuppressionList, assess_lead_lia
from engine.connectors.openapi_italy import OpenapiItalyClient
from engine.connectors.places_connector import PlacesDiscoveryClient, is_within_geo_filter
from engine.connectors.vies_validator import ViesValidatorClient
from engine.enrichment.gemini_qualifier import GeminiQualifier
from engine.enrichment.tech_audit import TechAuditor
from engine.schemas.campaign import CampaignConfig
from engine.schemas.lead import LeadRecord
from src.normalizers import (
    clean_company_website,
    is_anti_persona_retail,
    is_mobile_e164,
    normalize_email,
    normalize_phone_e164,
)
from src.piva_validator import clean_piva, validate_piva

logger = logging.getLogger("pipeline_runner")


class EnrichmentPipelineRunner:
    """Esegue la pipeline modulare con tracciamento costi e controlli GDPR."""

    def __init__(self, suppression: Optional[SuppressionList] = None):
        self.places = PlacesDiscoveryClient()
        self.vies = ViesValidatorClient()
        self.tech_auditor = TechAuditor()
        self.gemini = GeminiQualifier()
        self.suppression = suppression or SuppressionList()

    @staticmethod
    def deduplicate_leads(leads: List[LeadRecord]) -> List[LeadRecord]:
        """Deduplica prima dell'enrichment costoso per P.IVA, Telefono E.164 e (Nome, Città)."""
        seen_vat = set()
        seen_phone = set()
        seen_name_city = set()
        unique: List[LeadRecord] = []

        for lead in leads:
            vat = lead.vat_id.strip().upper()
            ph = lead.phone_e164.strip()
            nc = (lead.company_name.strip().lower(), lead.city.strip().lower())

            if vat and vat in seen_vat:
                continue
            if ph and ph in seen_phone:
                continue
            if nc in seen_name_city:
                continue

            if vat:
                seen_vat.add(vat)
            if ph:
                seen_phone.add(ph)
            seen_name_city.add(nc)
            unique.append(lead)

        return unique

    async def run_campaign(
        self,
        campaign: CampaignConfig,
        seed_leads: Optional[List[LeadRecord]] = None,
    ) -> Dict[str, object]:
        """
        Esegue l'imbuto completo sui seed forniti o scoperti via Places API.
        Restituisce dict con 'leads', 'stats', 'total_cost_eur'.
        """
        raw_leads = list(seed_leads or [])
        if not raw_leads:
            seed_res = await self.places.search_campaign_seeds(campaign)
            raw_leads = seed_res.get("leads") or []

        # Step 0: Geo-Lock + Anti-Persona + Normalizzazione E.164/Web + Deduplica
        cleaned: List[LeadRecord] = []
        for lead in raw_leads:
            if is_anti_persona_retail(lead.company_name, lead.category, lead.website):
                continue
            if lead.address and not is_within_geo_filter(lead.address, lead.country_code, campaign.geo):
                continue
            if not lead.country_code or lead.country_code.upper() != campaign.geo.country_code.upper():
                if campaign.geo.strict_country_lock:
                    continue

            p1, p2 = normalize_phone_e164(lead.phone_e164)
            lead.phone_e164 = p1
            if p2 and not lead.phone_secondary:
                lead.phone_secondary = p2
            lead.phone_type = "Mobile" if is_mobile_e164(p1) else ("Fisso" if p1 else "Unknown")
            lead.website = clean_company_website(lead.website)
            lead.email = normalize_email(lead.email)
            cleaned.append(lead)

        leads = self.deduplicate_leads(cleaned)

        openapi_client = OpenapiItalyClient(max_budget_eur=campaign.enrichment.max_l3_budget_eur)
        sem = asyncio.Semaphore(10)

        async with aiohttp.ClientSession() as session:

            async def _enrich_single(lead: LeadRecord):
                async with sem:
                    # Livello 1: Tech Audit + MX + P.IVA da sito
                    if campaign.enrichment.enable_l1_tech_audit and lead.website:
                        audit = await self.tech_auditor.audit_website(
                            lead.website,
                            session=session,
                            check_mx=campaign.enrichment.enable_l1_mx_check,
                        )
                        lead.tech_audit = audit
                        if not lead.email and audit.emails_found:
                            lead.email = audit.emails_found[0]
                            lead.email_mx_valid = audit.email_mx_valid
                        if not lead.pec and audit.pec_found:
                            lead.pec = audit.pec_found
                        if not lead.vat_id and audit.pivas_found:
                            lead.vat_id = f"IT{audit.pivas_found[0]}"
                    elif campaign.enrichment.enable_l1_mx_check and lead.email:
                        lead.email_mx_valid = await self.tech_auditor.verify_email_mx(lead.email)

                    # Validazione gratuita VIES UE se c'è P.IVA
                    if campaign.enrichment.enable_l1_vies and lead.vat_id:
                        digits = clean_piva(lead.vat_id)
                        if digits and validate_piva(digits):
                            vies_res = await self.vies.check_vat(lead.vat_id, default_country=lead.country_code, session=session)
                            if vies_res.get("status") == "OK":
                                lead.registry.vies_valid = vies_res.get("is_valid")
                                lead.registry.vies_name = vies_res.get("name", "")
                                lead.registry.vies_address = vies_res.get("address", "")
                                lead.registry.vies_request_id = vies_res.get("request_identifier", "")
                                lead.registry.source = "VIES_EU"

                    # Livello 2: AI Context & Product Routing
                    if campaign.enrichment.enable_l2_gemini_ai:
                        lead.ai_qualification = await self.gemini.qualify_lead(
                            lead,
                            offer_summary=campaign.offer_summary,
                            override_product=campaign.default_upsell_product,
                        )
                    else:
                        lead.ai_qualification = self.gemini.deterministic_qualify(
                            lead,
                            offer_summary=campaign.offer_summary,
                            override_product=campaign.default_upsell_product,
                        )

                    # Livello 3: Openapi.com solo su Tier A/B (risparmio crediti) e con P.IVA valida
                    if (
                        campaign.enrichment.enable_l3_openapi_registry
                        and lead.vat_id
                        and ("Tier A" in lead.ai_qualification.lead_tier or "Tier B" in lead.ai_qualification.lead_tier)
                        and openapi_client.has_credentials()
                    ):
                        reg_res = await openapi_client.query_company(
                            lead.vat_id,
                            endpoint=campaign.enrichment.l3_endpoint,
                            session=session,
                        )
                        if reg_res.get("status") == "OK":
                            lead.registry.ateco_code = reg_res.get("ateco_code", "")
                            lead.registry.ateco_description = reg_res.get("ateco_description", "")
                            lead.registry.forma_giuridica = reg_res.get("forma_giuridica", "")
                            lead.registry.rea_code = reg_res.get("rea_code", "")
                            lead.registry.cciaa = reg_res.get("cciaa", "")
                            lead.registry.activity_status = reg_res.get("activity_status", "")
                            lead.registry.sdi_code = reg_res.get("sdi_code", "")
                            lead.registry.pec_registry = reg_res.get("pec", "")
                            lead.registry.revenue_eur = reg_res.get("revenue_eur")
                            lead.registry.employees_count = reg_res.get("employees_count")
                            lead.registry.source = f"OPENAPI_{campaign.enrichment.l3_endpoint}"
                            if not lead.pec and lead.registry.pec_registry:
                                lead.pec = lead.registry.pec_registry
                            if not reg_res.get("cached"):
                                lead.enrichment_cost_eur += float(reg_res.get("estimated_cost_eur", 0.0))

                            # Ri-allinea routing & icebreaker se l'ATECO ufficiale è arrivato da Livello 3
                            if lead.registry.ateco_code:
                                lead.ai_qualification = self.gemini.deterministic_qualify(
                                    lead,
                                    offer_summary=campaign.offer_summary,
                                    override_product=campaign.default_upsell_product,
                                )

                    # Conformità B2B GDPR: LIA 3 fasi + blocco PEC + avviso RPO
                    lead.lia = assess_lead_lia(
                        lead=lead,
                        campaign_purpose=f"{campaign.target_vertical}: {campaign.offer_summary}",
                        has_optout_clause=True,
                        suppression=self.suppression,
                    )

            await asyncio.gather(*(_enrich_single(ld) for ld in leads))

        total_cost = round(sum(ld.enrichment_cost_eur for ld in leads), 4)
        stats = {
            "raw_count": len(raw_leads),
            "clean_deduped_count": len(leads),
            "lia_pass": sum(1 for ld in leads if ld.lia and ld.lia.status == "PASS"),
            "lia_review": sum(1 for ld in leads if ld.lia and ld.lia.status == "REVIEW_REQUIRED"),
            "lia_blocked": sum(1 for ld in leads if ld.lia and ld.lia.status == "BLOCKED"),
            "callable_e164": sum(1 for ld in leads if ld.phone_e164),
            "ordinary_emails": sum(1 for ld in leads if ld.email),
            "vies_valid": sum(1 for ld in leads if ld.registry.vies_valid is True),
            "total_cost_eur": total_cost,
        }
        return {"leads": leads, "stats": stats, "total_cost_eur": total_cost}
