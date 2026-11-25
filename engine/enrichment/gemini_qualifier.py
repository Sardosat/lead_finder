"""
gemini_qualifier.py — Livello 2 Enrichment con Google Gemini 2.5 Flash (Structured Outputs)
e fallback deterministico offline.

Vincoli inderogabili (AGENTS.md §2):
- Zero Hallucination: ogni pain point e citazione deve derivare da prove reali in TechAudit/Registry.
- Routing prodotto coerente su monetizelab.online, rsksystem.com o tecnicolive.it.
"""

import asyncio
import json
import logging
import os
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from engine.routing.product_router import PRODUCT_CATALOG, route_lead_to_product
from engine.enrichment.swot_analyzer import analyze_lead_swot_and_brief
from engine.schemas.lead import AIQualificationData, LeadRecord
from src.clay_engine import extract_semantic_signals
from src.config import ROOT_DIR
from src.normalizers import is_mobile_e164, is_strict_e164_italian, is_valid_company_website

logger = logging.getLogger("gemini_qualifier")


class _GeminiStructuredResponse(BaseModel):
    business_model: str = "Unknown"
    company_summary: str = ""
    detected_pain_points: List[str] = Field(default_factory=list)
    evidence_quotes: List[str] = Field(default_factory=list)
    icp_fit_score: int = 0
    outreach_angle: str = ""
    icebreaker_1to1: str = ""


class GeminiQualifier:
    """Qualificatore AI Livello 2 con Gemini 2.5 Flash Structured Outputs e fallback deterministico."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        load_dotenv(ROOT_DIR / ".env", override=False)
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = model_name

    def _compute_base_score(self, lead: LeadRecord) -> int:
        score = 0
        if is_mobile_e164(lead.phone_e164):
            score += 25
        elif is_strict_e164_italian(lead.phone_e164):
            score += 15

        if lead.email and lead.email_mx_valid is not False:
            score += 15
        if lead.vat_id:
            score += 20
        if lead.registry.vies_valid is True or lead.registry.ateco_code:
            score += 10
        if is_valid_company_website(lead.website):
            score += 15
            if lead.tech_audit.http_status == 200:
                score += 5
        if lead.tech_audit.text_snippet or lead.google_reviews_count:
            score += 10

        score = min(100, score)
        if not lead.phone_e164 and not lead.email:
            score = min(score, 45)
        return score

    @staticmethod
    def _score_to_tier(score: int, has_contact: bool) -> str:
        if score >= 80 and has_contact:
            return "Tier A 🔥 (VIP / Priorità Immediata)"
        if score >= 55 and has_contact:
            return "Tier B 🟡 (Warm / Retargeting RSK)"
        return "Tier C ❄️ (Cold / Da Arricchire)" if not has_contact else "Tier C ❄️ (Cold / Nurturing)"

    def deterministic_qualify(
        self,
        lead: LeadRecord,
        offer_summary: str = "",
        override_product=None,
    ) -> AIQualificationData:
        """Qualificazione deterministica 100% basata su segnali reali osservati (zero allucinazioni)."""
        routed = route_lead_to_product(
            company_name=lead.company_name,
            category=lead.category,
            niche=lead.niche,
            ateco_code=lead.registry.ateco_code,
            website_text=lead.tech_audit.text_snippet,
            override_product=override_product,
        )
        prod_key = routed["product_key"]
        prod_url = routed["product_url"]

        pain_points: List[str] = []
        evidence: List[str] = []

        if lead.website and lead.tech_audit.http_status == 200:
            if not lead.tech_audit.has_ssl:
                pain_points.append("Sito web privo di HTTPS/SSL attivo")
                evidence.append(f"URL rilevato senza SSL: {lead.website}")
            if not lead.tech_audit.has_whatsapp_cta:
                pain_points.append("Assenza di CTA diretta WhatsApp sul sito per risposta immediata")
                evidence.append("Audit HTML: nessun link wa.me / api.whatsapp.com rilevato")
            if not lead.tech_audit.has_booking_or_quote_form:
                pain_points.append("Nessun flusso di prenotazione / richiesta preventivo online strutturato")
                evidence.append("Audit HTML: assenza widget booking o form preventivi")
            if "Meta Pixel" not in lead.tech_audit.tracking_pixels and prod_key in ("monetizelab", "rsksystem"):
                pain_points.append("Assenza Meta Pixel sul sito (impossibile fare retargeting automatico)")
                evidence.append(f"Pixel rilevati: {lead.tech_audit.tracking_pixels or ['Nessuno']}")
        elif not lead.website:
            pain_points.append("Assenza di sito web aziendale proprietario verificato")
            evidence.append("Nessun dominio aziendale reale presente nel profilo")

        sem = extract_semantic_signals(
            text_corpus=f"{lead.company_name} {lead.category} {lead.niche}",
            company_name=lead.company_name,
            niche=lead.niche,
            website_text=lead.tech_audit.text_snippet,
        )
        if sem["marchi_verificati"]:
            evidence.append(f"Marchi rilevati realmente: {sem['marchi_str']}")
        if sem["is_h24"]:
            pain_points.append("Servizio reperibilità/emergenza attivo (alto rischio chiamate perse fuori orario)")
            evidence.append("Segnale H24 / pronto intervento presente nei testi aziendali")

        city_lbl = lead.city or "Italia"
        sector_lbl = lead.category or lead.niche or "la vostra attività"

        if prod_key == "tecnicolive":
            brand_part = f" (specializzati su {sem['marchi_str']})" if sem["marchi_verificati"] else ""
            icebreaker = (
                f"Buongiorno {lead.company_name}, vi contatto da Sinergia Rete d'Imprese / TecnicoLIVE. "
                f"Operando a {city_lbl} nel settore {sector_lbl}{brand_part}, con il nostro assistente vocale AI "
                f"non perdete chiamate in cantiere (chiamate simultanee illimitate) e per i non associati "
                f"attivate CNA Catania al 50% per tutto il primo anno."
            )
            angle = "Recupero chiamate perse in cantiere + pre-diagnosi guasti su WhatsApp"
        elif prod_key == "monetizelab":
            pixel_note = (
                "Abbiamo notato che sul sito non risulta un Meta Pixel attivo"
                if lead.website and lead.tech_audit.http_status == 200 and "Meta Pixel" not in lead.tech_audit.tracking_pixels
                else f"Seguendo agenzie e creator nella zona di {city_lbl}"
            )
            icebreaker = (
                f"Buongiorno {lead.company_name}, vi scrivo da MonetizeLab. {pixel_note}: "
                f"aiutiamo agenzie e content creator a trasformare la lead generation locale in pacchetti "
                f"ricorrenti ad alto margine senza dipendere dai limiti di LinkedIn."
            )
            angle = "Automazione acquisizione clienti locali & monetizzazione per agenzie/creator"
        else:
            gap_note = (
                "Abbiamo notato sul sito che manca una CTA diretta su WhatsApp o prenotazione rapida"
                if lead.website and lead.tech_audit.http_status == 200 and not lead.tech_audit.has_whatsapp_cta
                else f"Per le PMI di {sector_lbl} a {city_lbl}"
            )
            icebreaker = (
                f"Buongiorno {lead.company_name}, vi contatto da RSK System. {gap_note}: "
                f"con la nostra piattaforma CRM + Smart Lists WhatsApp ed Email trasformate i contatti "
                f"locali in appuntamenti automatici senza disperdere richieste."
            )
            angle = "Nutrimento lead su CRM RSK System + follow-up automatico WhatsApp/Email"

        score = self._compute_base_score(lead)
        has_contact = bool(lead.phone_e164 or lead.email)
        summary = (
            f"{lead.company_name} opera nel settore {sector_lbl} a {city_lbl}. "
            f"Prodotto ecosistema consigliato: {PRODUCT_CATALOG[prod_key]['name']}."
        )

        swot = analyze_lead_swot_and_brief(
            company_name=lead.company_name,
            city=lead.city,
            niche=lead.niche,
            category=lead.category,
            phone_e164=lead.phone_e164,
            phone_type=lead.phone_type,
            email=lead.email,
            email_mx_valid=lead.email_mx_valid,
            pec=lead.pec,
            website=lead.website,
            has_valid_piva=bool(lead.vat_id),
            vies_valid=lead.registry.vies_valid,
            brands=sem["marchi"],
            certifications=[c.strip() for c in sem["certificazioni"].split(",") if c.strip() and c.strip() != "Non rilevate"],
            is_h24=sem["is_h24"],
            http_status=lead.tech_audit.http_status,
            has_ssl=lead.tech_audit.has_ssl,
            cms_stack=lead.tech_audit.cms_stack,
            tracking_pixels=lead.tech_audit.tracking_pixels,
            has_whatsapp_cta=lead.tech_audit.has_whatsapp_cta,
            has_booking_or_quote_form=lead.tech_audit.has_booking_or_quote_form,
            social_links=lead.tech_audit.social_links,
            employees_count=lead.registry.employees_count,
            revenue_eur=lead.registry.revenue_eur,
            forma_giuridica=lead.registry.forma_giuridica,
            recommended_product=prod_key,
            recommended_product_name=PRODUCT_CATALOG[prod_key]["name"],
        )

        return AIQualificationData(
            model_used="deterministic",
            business_model="B2B2C" if prod_key in ("tecnicolive", "rsksystem") else "B2B",
            company_summary=summary,
            detected_pain_points=pain_points or [p.title for p in swot["pain_signals"]] or ["Opportunità di automazione acquisizione e risposta rapida"],
            evidence_quotes=evidence,
            pain_signals=swot["pain_signals"],
            weak_points=swot["weak_points"],
            strengths=swot["strengths"],
            sales_brief=swot["sales_brief"],
            icp_fit_score=score,
            lead_tier=self._score_to_tier(score, has_contact),
            recommended_product=prod_key,
            recommended_product_url=prod_url,
            outreach_angle=angle,
            icebreaker_1to1=icebreaker,
        )

    async def qualify_lead(
        self,
        lead: LeadRecord,
        offer_summary: str = "",
        override_product=None,
    ) -> AIQualificationData:
        """Usa Gemini 2.5 Flash (Structured Outputs) se GEMINI_API_KEY presente, altrimenti fallback deterministico."""
        det = self.deterministic_qualify(lead, offer_summary=offer_summary, override_product=override_product)
        if not self.api_key:
            return det

        try:
            from google import genai
            from google.genai import types

            routed = route_lead_to_product(
                company_name=lead.company_name,
                category=lead.category,
                niche=lead.niche,
                ateco_code=lead.registry.ateco_code,
                website_text=lead.tech_audit.text_snippet,
                override_product=override_product,
            )

            prompt = (
                "Sei un analista GTM B2B italiano conforme a GDPR e Zero Hallucination Policy.\n"
                "Analizza SOLO i dati reali seguenti (non inventare MAI marchi, recensioni o statistiche assenti):\n"
                f"- Ragione Sociale: {lead.company_name}\n"
                f"- Città/Provincia: {lead.city} ({lead.province}), {lead.country_code}\n"
                f"- Categoria/ATECO: {lead.category} | ATECO: {lead.registry.ateco_code}\n"
                f"- Sito Web: {lead.website or 'Assente'} | HTTP: {lead.tech_audit.http_status} | SSL: {lead.tech_audit.has_ssl}\n"
                f"- CMS: {lead.tech_audit.cms_stack} | Pixel: {lead.tech_audit.tracking_pixels} | "
                f"WhatsApp CTA: {lead.tech_audit.has_whatsapp_cta} | Booking/Preventivo: {lead.tech_audit.has_booking_or_quote_form}\n"
                f"- Prodotto Ecosistema Target: {routed['product_name']} ({routed['product_url']}) — {routed['core_pitch']}\n"
                f"- Offerta Campagna: {offer_summary}\n"
                f"- Estratto Reale Sito: {lead.tech_audit.text_snippet[:2500]}\n\n"
                "Restituisci un JSON aderente allo schema: business_model (B2B/B2C/B2B2C), company_summary (1-2 frasi in italiano), "
                "detected_pain_points (solo basati sui dati tecnici/testo sopra), evidence_quotes (citazioni brevi reali dal testo/audit), "
                "icp_fit_score (0-100), outreach_angle, icebreaker_1to1 (massimo 3 frasi, tono pragmatico senza cliché AI)."
            )

            def _call_gemini():
                client = genai.Client(api_key=self.api_key)
                return client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                        response_schema=_GeminiStructuredResponse,
                    ),
                )

            resp = await asyncio.to_thread(_call_gemini)
            raw_json = json.loads(resp.text or "{}")
            parsed = _GeminiStructuredResponse(**raw_json)

            bm = parsed.business_model if parsed.business_model in ("B2B", "B2C", "B2B2C", "Unknown") else "Unknown"
            has_contact = bool(lead.phone_e164 or lead.email)
            score = max(0, min(100, int(parsed.icp_fit_score)))
            if not has_contact:
                score = min(score, 45)

            return AIQualificationData(
                model_used=self.model_name,
                business_model=bm,
                company_summary=parsed.company_summary or det.company_summary,
                detected_pain_points=parsed.detected_pain_points or det.detected_pain_points,
                evidence_quotes=parsed.evidence_quotes or det.evidence_quotes,
                pain_signals=det.pain_signals,
                weak_points=det.weak_points,
                strengths=det.strengths,
                sales_brief=det.sales_brief,
                icp_fit_score=score,
                lead_tier=self._score_to_tier(score, has_contact),
                recommended_product=det.recommended_product,
                recommended_product_url=det.recommended_product_url,
                outreach_angle=parsed.outreach_angle or det.outreach_angle,
                icebreaker_1to1=parsed.icebreaker_1to1 or det.icebreaker_1to1,
            )
        except Exception as e:
            logger.warning(f"Fallback deterministico per Gemini ({lead.company_name}): {e}")
            return det
