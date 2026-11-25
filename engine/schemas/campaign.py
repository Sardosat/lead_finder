from typing import List, Literal, Optional
from pydantic import BaseModel, Field

UpsellProduct = Literal["monetizelab", "rsksystem", "tecnicolive"]


class GeoFilter(BaseModel):
    """Filtro geografico rigoroso basato su codice paese, provincia, comuni e codici ISTAT."""

    country_code: str = "IT"
    region: str = ""
    province_code: str = ""
    municipalities: List[str] = Field(default_factory=list)
    istat_codes: List[str] = Field(default_factory=list)
    strict_country_lock: bool = True


class EnrichmentLevels(BaseModel):
    """Controllo progressivo a 3 livelli dell'imbuto di enrichment e budget API."""

    enable_l1_tech_audit: bool = True
    enable_l1_mx_check: bool = True
    enable_l1_vies: bool = True
    enable_l2_gemini_ai: bool = True
    enable_l3_openapi_registry: bool = False
    l3_endpoint: Literal["IT-start", "IT-advanced"] = "IT-start"
    max_l3_budget_eur: float = 5.0


class CampaignConfig(BaseModel):
    """Configurazione di una campagna multi-settore configurabile per qualsiasi nicchia IT/EU."""

    campaign_id: str
    name: str
    target_vertical: str
    ateco_codes: List[str] = Field(default_factory=list)
    nace_codes: List[str] = Field(default_factory=list)
    search_queries: List[str] = Field(default_factory=list)
    geo: GeoFilter = Field(default_factory=GeoFilter)
    default_upsell_product: Optional[UpsellProduct] = None
    offer_summary: str
    enrichment: EnrichmentLevels = Field(default_factory=EnrichmentLevels)
    max_results_per_query: int = 20
