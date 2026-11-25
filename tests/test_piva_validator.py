from src.piva_validator import clean_piva, extract_piva_candidates, validate_piva


def test_clean_piva_handles_prefix_and_spaces():
    assert clean_piva("IT06200390877") == "06200390877"
    assert clean_piva("it 06200390877") == "06200390877"
    assert clean_piva("IT-062.003.90877") == "06200390877"
    assert clean_piva("12345") is None
    assert clean_piva("") is None


def test_validate_piva_luhn():
    assert validate_piva("IT06200390877") is True
    assert validate_piva("06200390877") is True
    assert validate_piva("IT06200390878") is False
    assert validate_piva("00000000000") is False
    assert validate_piva("1234567890") is False


def test_extract_piva_candidates_from_text():
    html = """
    <footer>
        Ragione Sociale Test Srl - P.IVA: IT 06200390877 - Tel 0951234567
        Altra P.IVA non valida: 06200390878
    </footer>
    """
    candidates = extract_piva_candidates(html)
    assert candidates == ["06200390877"]
