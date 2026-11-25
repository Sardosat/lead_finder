from src.normalizers import (
    clean_company_website,
    is_anti_persona_retail,
    is_maltese_or_foreign_record,
    is_mobile_e164,
    is_strict_e164_italian,
    is_valid_company_website,
    normalize_email,
    normalize_phone_e164,
)


def test_normalize_phone_e164_single_and_multi():
    assert normalize_phone_e164("347 7446410") == ("+393477446410", "")
    assert normalize_phone_e164("+39 095 7704550") == ("+390957704550", "")
    assert normalize_phone_e164("095/7139656") == ("+390957139656", "")
    # Multi-numero: privilegia mobile come primario
    p1, p2 = normalize_phone_e164("095 9898016 / 347 9974534 / 328 2166454")
    assert p1 == "+393479974534"
    assert p2 == "+393282166454 | +390959898016"
    assert is_strict_e164_italian(p1) is True
    assert is_mobile_e164(p1) is True


def test_normalize_phone_rejects_maltese_and_empty():
    assert normalize_phone_e164("+356 21234567") == ("", "")
    assert normalize_phone_e164("00356 99112233") == ("", "")
    assert normalize_phone_e164("") == ("", "")
    assert normalize_phone_e164("N/D") == ("", "")


def test_website_blacklist_filters_portals_and_keeps_real_sites():
    assert is_valid_company_website("https://www.pgcasa.it") is False
    assert is_valid_company_website("https://www.paginebianche.it") is False
    assert is_valid_company_website("https://www.paginegialle.it/azienda") is False
    assert is_valid_company_website("https://www.1240.it/") is False
    assert is_valid_company_website("https://www.facebook.com/ditta") is False
    assert clean_company_website("https://www.pgcasa.it") == ""

    assert is_valid_company_website("https://www.cantarellaclima.it") is True
    assert clean_company_website("climasolservice.it/") == "https://climasolservice.it"


def test_anti_persona_filters_gdo_but_preserves_legitimate_trades():
    # GDO & non-trade da filtrare
    assert is_anti_persona_retail("Kasanova C/O Etnapolis", "Casalinghi") is True
    assert is_anti_persona_retail("Trony Papino Elettrodomestici", "Elettrodomestici") is True
    assert is_anti_persona_retail("Mediaworld C/O Porte di Catania", "Elettrodomestici") is True
    assert is_anti_persona_retail("Euronics - Bruno c/o Le Zagare", "Elettrodomestici") is True
    assert is_anti_persona_retail("Bruno S.p.a.", "Elettrodomestici") is True
    assert is_anti_persona_retail("Happy Casa C/O I Portali", "") is True
    assert is_anti_persona_retail("Gamelife C/O Centro Sicilia", "") is True
    assert is_anti_persona_retail("Al Soccorso Televisivo", "Television repair service") is True
    assert is_anti_persona_retail("D'Urso Giuseppe Autofficina", "Autofficine e centri assistenza") is True
    assert is_anti_persona_retail("Eni Plenitude Flagship Store", "Energy supplier") is True

    # Aziende legittime da NON filtrare mai (attenzione a "bruno" e "auto")
    assert is_anti_persona_retail("Donini Bruno di Donini Dario", "Riscaldamento - impianti e manutenzione") is False
    assert is_anti_persona_retail("Coel Cancelli Automatici", "Cancelli, porte e portoni automatici e telecomandati") is False
    assert is_anti_persona_retail("Climasolservice srl", "Impianti condizionamento aria") is False
    assert is_anti_persona_retail("Cantarella Clima • Vaillant Service Plus", "Caldaie e scaldabagni") is False


def test_maltese_record_detection():
    assert is_maltese_or_foreign_record({"Country": "MT", "City": "Qormi", "Phone": "+35621223344"}) is True
    assert is_maltese_or_foreign_record({"Country": "IT", "City": "Catania", "Phone": "+39095123456"}) is False


def test_normalize_email():
    assert normalize_email("  INFO@CantarellaClima.IT ") == "info@cantarellaclima.it"
    assert normalize_email("mailto:test@climasolservice.it?subject=Hi") == "test@climasolservice.it"
    assert normalize_email("noreply@paginegialle.it") == ""
