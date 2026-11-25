from typing import List, Literal
from pydantic import BaseModel, Field


class LIATestStage(BaseModel):
    """Esito di una delle 3 fasi obbligatorie del Legitimate Interest Assessment (Art. 6.1.f GDPR)."""

    passed: bool
    rationale: str


class LIAAssessment(BaseModel):
    """Valutazione formale B2B GDPR LIA, blocco PEC e avviso RPO."""

    status: Literal["PASS", "REVIEW_REQUIRED", "BLOCKED"]
    legal_basis: str = "Art. 6(1)(f) GDPR — Legitimate Interest B2B"
    purpose_test: LIATestStage
    necessity_test: LIATestStage
    balancing_test: LIATestStage
    pec_cold_outreach_blocked: bool = False
    rpo_check_required: bool = False
    optout_mechanism_present: bool = True
    suppressed: bool = False
    assessed_at: str = ""
    notes: List[str] = Field(default_factory=list)
