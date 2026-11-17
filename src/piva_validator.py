import re
from typing import Optional


def clean_piva(raw: str) -> Optional[str]:
    """
    Pulisce e normalizza una stringa Partita IVA:
    - Rimuove prefisso IT / it / it. / it- (incluso spazi intermedi es. 'IT 06200390877')
    - Rimuove spazi, punti o trattini
    - Restituisce la stringa di 11 cifre o None se non conforme
    """
    if not raw:
        return None
    
    cleaned = raw.strip().upper()
    
    # Rimuove prefisso IT o IT- o IT.
    cleaned = re.sub(r"^IT[\s\.\-_]*", "", cleaned)
    
    # Rimuove tutti i caratteri non numerici
    digits = re.sub(r"\D", "", cleaned)
    
    if len(digits) == 11:
        return digits
    return None


def validate_piva(piva_candidate: str) -> bool:
    """
    Verifica la validità dell'algoritmo di controllo della Partita IVA italiana (D.P.R. 633/1972).
    Accetta P.IVA con o senza prefisso 'IT'.
    """
    digits = clean_piva(piva_candidate)
    if not digits:
        return False
    
    # Non può essere composta da soli zeri
    if digits == "00000000000":
        return False

    # Algoritmo ufficiale (Luhn variante italiana)
    s1 = sum(int(digits[i]) for i in (0, 2, 4, 6, 8))
    
    s2 = 0
    for i in (1, 3, 5, 7, 9):
        doubled = int(digits[i]) * 2
        s2 += doubled if doubled <= 9 else (doubled - 9)
    
    total = s1 + s2
    expected_check_digit = (10 - (total % 10)) % 10
    
    actual_check_digit = int(digits[10])
    return expected_check_digit == actual_check_digit


def extract_piva_candidates(text: str) -> list[str]:
    """
    Estrae tutti i candidati P.IVA validati matematicamente da un blocco di testo o HTML.
    Gestisce prefissi IT opzionali, etichette 'P.IVA', 'Partita IVA', 'C.F./P.IVA', ecc.
    """
    if not text:
        return []
    
    # Pattern per catturare sia 'IT12345678901' che 'P.IVA 12345678901' che numeri a 11 cifre isolati
    patterns = [
        r"(?:IT|it)[\s\.\-_]*([0-9]{11})\b",
        r"(?:P\.?\s*IVA|PARTITA\s+IVA|P\.\s*I\.|CODICE\s+FISCALE)[\s\:\.\-_]*([0-9]{11})\b",
        r"\b([0-9]{11})\b"
    ]
    
    found_valid = []
    seen = set()
    
    for pat in patterns:
        matches = re.finditer(pat, text, flags=re.IGNORECASE)
        for m in matches:
            cand = m.group(1) if m.groups() else m.group(0)
            cleaned = clean_piva(cand)
            if cleaned and cleaned not in seen:
                if validate_piva(cleaned):
                    seen.add(cleaned)
                    found_valid.append(cleaned)
                    
    return found_valid

