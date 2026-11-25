from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from engine.schemas.campaign import UpsellProduct
from engine.schemas.compliance import LIAAssessment


class TechAuditData(BaseModel):
    """Livello 1: Audit tecnico del sito web, stack CMS, pixel, CTA e validazione MX."""

    http_status: int = 0
    has_ssl: bool = False
    cms_stack: str = "Unknown"
    tracking_pixels: List[str] = Field(default_factory=list)
    has_whatsapp_cta: bool = False
    has_booking_or_quote_form: bool = False
    social_links: Dict[str, str] = Field(default_factory=dict)
    emails_found: List[str] = Field(default_factory=list)
    pec_found: str = ""
    email_mx_valid: Optional[bool] = None
    pivas_found: List[str] = Field(default_factory=list)
    text_snippet: str = ""


class RegistryData(BaseModel):
    """Livello 3 & VIES: Dati fiscali, camerali, ATECO/NACE e certificazioni ufficiali."""

    vies_valid: Optional[bool] = None
    vies_name: str = ""
    vies_address: str = ""
    vies_request_id: str = ""
    ateco_code: str = ""
    ateco_description: str = ""
    nace_code: str = ""
    forma_giuridica: str = ""
    rea_code: str = ""
    cciaa: str = ""
    activity_status: str = ""
    sdi_code: str = ""
    pec_registry: str = ""
    revenue_eur: Optional[float] = None
    employees_count: Optional[int] = None
    albi_certificazioni: List[str] = Field(default_factory=list)
    source: str = ""


class LeadSignalItem(BaseModel):
    """Singolo segnale verificato (Pain Point, Weak Point o Strength) per il dossier pre-chiamata."""

    id: str
    kind: Literal["pain", "weak", "strength"]
    category: str
    title: str
    description: str
    severity: Literal["high", "medium", "low"] = "medium"
    icon: str = "target"
    color: Literal["red", "amber", "emerald", "blue", "purple"] = "blue"
    evidence: str = ""
    attack_angle: str = ""


class PreCallSalesBrief(BaseModel):
    """Brief operativo pre-chiamata: cosa vendere al lead e perché."""

    product_key: UpsellProduct = "rsksystem"
    product_name: str = "RSK System"
    recommended_plan: str = ""
    company_size_label: str = "PMI / Da verificare"
    tech_maturity_label: str = "Base"
    why_sell: str = ""
    primary_pain_to_attack: str = ""
    leverage_strength: str = ""
    suggested_opener: str = ""
    expected_objection: str = ""


class AIQualificationData(BaseModel):
    """Livello 2: Qualificazione AI contestuale, pain point reali e routing prodotto."""

    model_used: str = "deterministic"
    business_model: Literal["B2B", "B2C", "B2B2C", "Unknown"] = "Unknown"
    company_summary: str = ""
    detected_pain_points: List[str] = Field(default_factory=list)
    evidence_quotes: List[str] = Field(default_factory=list)
    pain_signals: List[LeadSignalItem] = Field(default_factory=list)
    weak_points: List[LeadSignalItem] = Field(default_factory=list)
    strengths: List[LeadSignalItem] = Field(default_factory=list)
    sales_brief: Optional[PreCallSalesBrief] = None
    icp_fit_score: int = 0
    lead_tier: str = "Tier C"
    recommended_product: UpsellProduct = "rsksystem"
    recommended_product_url: str = "https://rsksystem.com"
    outreach_angle: str = ""
    icebreaker_1to1: str = ""


class LeadRecord(BaseModel):
    """Schema canonico italiano/europeo per ogni impresa qualificata dal Lead Engine."""

    company_name: str
    vat_id: str = ""
    tax_code: str = ""
    country_code: str = "IT"
    region: str = ""
    province: str = ""
    city: str = ""
    istat_code: str = ""
    postal_code: str = ""
    address: str = ""

    phone_e164: str = ""
    phone_secondary: str = ""
    phone_type: Literal["Mobile", "Fisso", "Unknown"] = "Unknown"
    email: str = ""
    email_mx_valid: Optional[bool] = None
    pec: str = ""
    website: str = ""

    source: str = "manual"
    google_place_id: str = ""
    google_rating: Optional[float] = None
    google_reviews_count: Optional[int] = None
    category: str = ""
    niche: str = ""

    tech_audit: TechAuditData = Field(default_factory=TechAuditData)
    registry: RegistryData = Field(default_factory=RegistryData)
    ai_qualification: AIQualificationData = Field(default_factory=AIQualificationData)
    lia: Optional[LIAAssessment] = None
    enrichment_cost_eur: float = 0.0
