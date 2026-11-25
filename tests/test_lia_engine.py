from pathlib import Path

from engine.compliance.lia_engine import SuppressionList, assess_lead_lia, is_pec_email
from engine.schemas.lead import LeadRecord


def test_is_pec_email_detection():
    assert is_pec_email("azienda@pec.it") is True
    assert is_pec_email("ditta@legalmail.it") is True
    assert is_pec_email("info@arubapec.it") is True
    assert is_pec_email("info@tecnicolive.it") is False


def test_lia_blocks_pec_from_outbound_and_flags_rpo(tmp_path: Path):
    sup = SuppressionList(csv_path=tmp_path / "sup.csv")
    lead = LeadRecord(
        company_name="Termoidraulica Etnea Srl",
        vat_id="IT06200390877",
        city="Catania",
        phone_e164="+393471234567",
        email="etnea@pec.it",
        category="Termoidraulica",
    )
    res = assess_lead_lia(lead, campaign_purpose="Convenzione CNA & TecnicoLIVE", suppression=sup)

    assert res.status == "PASS"
    assert res.pec_cold_outreach_blocked is True
    assert res.rpo_check_required is True
    assert lead.email == ""  # PEC svuotata dal canale email ordinario!
    assert lead.pec == "etnea@pec.it"


def test_lia_review_required_when_only_pec_exists_no_phone(tmp_path: Path):
    sup = SuppressionList(csv_path=tmp_path / "sup.csv")
    lead = LeadRecord(
        company_name="Studio Alfa Srl",
        vat_id="IT06200390877",
        city="Catania",
        phone_e164="",
        email="studioalfa@legalmail.it",
    )
    res = assess_lead_lia(lead, campaign_purpose="Offerta RSK System", suppression=sup)

    assert res.status == "REVIEW_REQUIRED"
    assert res.pec_cold_outreach_blocked is True
    assert lead.email == ""


def test_lia_blocks_suppressed_and_missing_optout(tmp_path: Path):
    sup = SuppressionList(csv_path=tmp_path / "sup.csv")
    sup.add_optout(phone_e164="+393470001122", reason="CANCELLAMI")

    lead_sup = LeadRecord(
        company_name="Ditta Beta Srl",
        city="Catania",
        phone_e164="+393470001122",
    )
    res_sup = assess_lead_lia(lead_sup, campaign_purpose="Test", suppression=sup)
    assert res_sup.status == "BLOCKED"
    assert res_sup.suppressed is True

    lead_no_opt = LeadRecord(
        company_name="Ditta Gamma Srl",
        city="Catania",
        phone_e164="+393479998877",
    )
    res_no_opt = assess_lead_lia(
        lead_no_opt, campaign_purpose="Test", has_optout_clause=False, suppression=sup
    )
    assert res_no_opt.status == "BLOCKED"
