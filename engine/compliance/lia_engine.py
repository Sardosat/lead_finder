"""
lia_engine.py — Motore di conformità B2B GDPR & Direttiva ePrivacy.
Implementa il Test di Legittimo Interesse a 3 fasi (Art. 6.1.f GDPR),
il blocco rigoroso di cold outreach su PEC, l'avviso RPO (Registro Pubblico Opposizioni)
e la lista di soppressione (Opt-Out).
"""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

from engine.schemas.compliance import LIAAssessment, LIATestStage
from engine.schemas.lead import LeadRecord
from src.config import DATA_DIR, ROOT_DIR
from src.normalizers import is_anti_persona_retail, is_strict_e164_italian

PEC_DOMAIN_HINTS = (
    "pec.",
    "@pec.",
    "@legalmail.",
    "@arubapec.",
    "@postecert.",
    "@cert.",
    "@gigapec.",
    "@sicurezzapostale.",
    "@registerpec.",
    "@namirialpec.",
    "@infocert.",
    "@telecompost.",
    "@cgn.legalmail.",
    "@actalispec.",
    ".pec.it",
)

DEFAULT_SUPPRESSION_CSV = DATA_DIR / "suppression_list.csv"
BLACKLIST_MD_PATH = ROOT_DIR / "quality_assurance" / "esclusioni_e_optout" / "blacklist_suppression.md"


def is_pec_email(email: str) -> bool:
    """Rileva se un indirizzo email è una PEC italiana (vietata per cold outreach commerciale)."""
    if not email or "@" not in email:
        return False
    em = email.strip().lower()
    return any(hint in em for hint in PEC_DOMAIN_HINTS)


class SuppressionList:
    """Gestisce l'elenco di opt-out / do-not-contact per telefono, email e P.IVA."""

    def __init__(self, csv_path: Path = DEFAULT_SUPPRESSION_CSV):
        self.csv_path = csv_path
        self.phones: Set[str] = set()
        self.emails: Set[str] = set()
        self.vats: Set[str] = set()
        self._load()

    def _load(self):
        if self.csv_path.exists():
            try:
                with open(self.csv_path, encoding="utf-8-sig", newline="") as f:
                    for row in csv.DictReader(f):
                        ph = (row.get("phone_e164") or "").strip()
                        em = (row.get("email") or "").strip().lower()
                        vat = (row.get("vat_id") or "").strip().upper()
                        if ph:
                            self.phones.add(ph)
                        if em:
                            self.emails.add(em)
                        if vat:
                            self.vats.add(vat)
            except Exception:
                pass

    def is_suppressed(self, phone_e164: str = "", email: str = "", vat_id: str = "") -> bool:
        if phone_e164 and phone_e164.strip() in self.phones:
            return True
        if email and email.strip().lower() in self.emails:
            return True
        if vat_id and vat_id.strip().upper() in self.vats:
            return True
        return False

    def add_optout(self, phone_e164: str = "", email: str = "", vat_id: str = "", reason: str = "CANCELLAMI"):
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        file_exists = self.csv_path.exists()
        with open(self.csv_path, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["timestamp_utc", "phone_e164", "email", "vat_id", "reason"]
            )
            if not file_exists:
                writer.writeheader()
            writer.writerow(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "phone_e164": phone_e164.strip(),
                    "email": email.strip().lower(),
                    "vat_id": vat_id.strip().upper(),
                    "reason": reason,
                }
            )
        if phone_e164.strip():
            self.phones.add(phone_e164.strip())
        if email.strip():
            self.emails.add(email.strip().lower())
        if vat_id.strip():
            self.vats.add(vat_id.strip().upper())

    def list_entries(self) -> List[Dict[str, str]]:
        """Restituisce tutte le righe della lista di soppressione in ordine cronologico inverso."""
        if not self.csv_path.exists():
            return []
        entries: List[Dict[str, str]] = []
        try:
            with open(self.csv_path, encoding="utf-8-sig", newline="") as f:
                for idx, row in enumerate(csv.DictReader(f)):
                    entries.append(
                        {
                            "id": str(idx + 1),
                            "timestamp_utc": (row.get("timestamp_utc") or "").strip(),
                            "phone_e164": (row.get("phone_e164") or "").strip(),
                            "email": (row.get("email") or "").strip().lower(),
                            "vat_id": (row.get("vat_id") or "").strip().upper(),
                            "reason": (row.get("reason") or "CANCELLAMI").strip(),
                        }
                    )
        except Exception:
            return []
        entries.reverse()
        return entries

    def remove_optout(self, phone_e164: str = "", email: str = "", vat_id: str = "") -> bool:
        """Rimuove le voci corrispondenti da CSV e ricarica i set in memoria."""
        if not self.csv_path.exists():
            return False
        target_ph = (phone_e164 or "").strip()
        target_em = (email or "").strip().lower()
        target_vat = (vat_id or "").strip().upper()
        if not (target_ph or target_em or target_vat):
            return False

        kept: List[Dict[str, str]] = []
        removed = False
        with open(self.csv_path, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                ph = (row.get("phone_e164") or "").strip()
                em = (row.get("email") or "").strip().lower()
                vat = (row.get("vat_id") or "").strip().upper()
                matches = (
                    (target_ph and ph == target_ph)
                    or (target_em and em == target_em)
                    or (target_vat and vat == target_vat)
                )
                if matches:
                    removed = True
                else:
                    kept.append(row)

        if not removed:
            return False

        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["timestamp_utc", "phone_e164", "email", "vat_id", "reason"]
        tmp_path = self.csv_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in kept:
                writer.writerow({k: row.get(k, "") for k in fieldnames})
        tmp_path.replace(self.csv_path)

        self.phones.clear()
        self.emails.clear()
        self.vats.clear()
        self._load()
        return True


def assess_lead_lia(
    lead: LeadRecord,
    campaign_purpose: str,
    has_optout_clause: bool = True,
    suppression: Optional[SuppressionList] = None,
) -> LIAAssessment:
    """
    Esegue il Test di Legittimo Interesse in 3 fasi (Purpose, Necessity, Balancing)
    secondo AGENTS.md §3 e normativa italiana/UE.
    Effetto collaterale intenzionale di sicurezza: se lead.email è una PEC, la sposta in lead.pec
    e svuota lead.email per impedire invii commerciali su PEC.
    """
    notes: List[str] = []
    pec_blocked = False

    # Protezione rigida anti-PEC in canale outbound ordinario
    if lead.email and is_pec_email(lead.email):
        pec_blocked = True
        if not lead.pec:
            lead.pec = lead.email.strip().lower()
        notes.append(
            f"PEC '{lead.pec}' isolata in campo registro: invio cold outreach su PEC bloccato."
        )
        lead.email = ""

    if lead.pec:
        pec_blocked = True

    # Fase 1: Purpose Test
    is_gdo_or_invalid = is_anti_persona_retail(lead.company_name, lead.category, lead.website)
    purpose_ok = bool(lead.company_name.strip()) and bool(campaign_purpose.strip()) and not is_gdo_or_invalid
    purpose_reason = (
        f"Comunicazione B2B strettamente pertinente all'attività professionale ({campaign_purpose[:80]})."
        if purpose_ok
        else "Impresa non valida o fuori perimetro B2B / Anti-Persona."
    )
    purpose_stage = LIATestStage(passed=purpose_ok, rationale=purpose_reason)

    # Fase 2: Necessity Test (minimizzazione dati)
    has_business_identity = bool(lead.company_name.strip()) and bool(
        lead.vat_id or lead.website or lead.city or lead.google_place_id
    )
    has_outbound_channel = bool(lead.phone_e164 or lead.email)
    necessity_ok = has_business_identity and has_outbound_channel
    necessity_reason = (
        "Dati limitati ai recapiti aziendali pubblici strettamente necessari (no dati sensibili, no PEC outbound)."
        if necessity_ok
        else "Manca recapito aziendale contattabile (telefono E.164 o email ordinaria non-PEC)."
    )
    necessity_stage = LIATestStage(passed=necessity_ok, rationale=necessity_reason)

    # Fase 3: Balancing Test
    sup = suppression or SuppressionList()
    is_suppressed = sup.is_suppressed(
        phone_e164=lead.phone_e164, email=lead.email, vat_id=lead.vat_id
    )
    rpo_required = is_strict_e164_italian(lead.phone_e164)
    if rpo_required:
        notes.append(
            "Telefono +39 presente: verificare esclusioni Registro Pubblico delle Opposizioni (RPO) prima di telemarketing."
        )

    balancing_ok = (not is_suppressed) and has_optout_clause
    if is_suppressed:
        bal_reason = "Contatto presente nella lista di soppressione / opt-out (DND)."
    elif not has_optout_clause:
        bal_reason = "Clausola opt-out B2B obbligatoria assente."
    else:
        bal_reason = "Contatto B2B pertinente, opt-out immediato e gratuito presente, nessuna invasività sproporzionata."
    balancing_stage = LIATestStage(passed=balancing_ok, rationale=bal_reason)

    if is_suppressed or not purpose_stage.passed or not has_optout_clause:
        status = "BLOCKED"
    elif not necessity_stage.passed:
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return LIAAssessment(
        status=status,
        purpose_test=purpose_stage,
        necessity_test=necessity_stage,
        balancing_test=balancing_stage,
        pec_cold_outreach_blocked=pec_blocked,
        rpo_check_required=rpo_required,
        optout_mechanism_present=has_optout_clause,
        suppressed=is_suppressed,
        assessed_at=datetime.now(timezone.utc).isoformat(),
        notes=notes,
    )
