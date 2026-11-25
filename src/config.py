from pathlib import Path

# Percorsi di lavoro
ROOT_DIR = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT_DIR / "CSV_Leads"

# Cartelle organizzate
DATA_DIR = ROOT_DIR / "data"                  # Dati CSV di lavoro (apribili nell'editor)
EXCEL_DIR = ROOT_DIR / "exports_excel"        # Tutti i file Excel (.xlsx) formattati
REPORTS_DIR = ROOT_DIR / "reports"            # Report PDF strategici

DATA_DIR.mkdir(exist_ok=True)
EXCEL_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Percorsi file Excel (in exports_excel/)
OUTPUT_DASHBOARD_EXCEL = EXCEL_DIR / "leads_cna_dashboard.xlsx"
OUTPUT_VERIFICA_CNA_EXCEL = EXCEL_DIR / "richiesta_verifica_cna.xlsx"
OUTPUT_DISCOVERED_EXCEL = EXCEL_DIR / "nuove_lead_scoperte.xlsx"

# Percorsi file CSV (in data/)
OUTPUT_DASHBOARD_CSV = DATA_DIR / "tutte_le_lead.csv"
OUTPUT_TARGET_CSV = DATA_DIR / "target_tesseramento_cna.csv"
OUTPUT_ASSOCIATI_CSV = DATA_DIR / "associati_rilevati.csv"
OUTPUT_VERIFICA_CNA_CSV = DATA_DIR / "richiesta_verifica_cna.csv"
OUTPUT_DISCOVERED_CSV = DATA_DIR / "nuove_lead_scoperte.csv"
OUTPUT_OUTBOUND_CSV = DATA_DIR / "campagna_outbound_tecnicolive.csv"
OUTPUT_DA_ARRICCHIRE_CSV = DATA_DIR / "da_arricchire_contatti.csv"
OUTPUT_TERMOIDRAULICA_CSV = DATA_DIR / "termoidraulica_catania_provincia.csv"
OUTPUT_CSV_ENRICHED = DATA_DIR / "leads_arricchiti.csv"
OUTPUT_RIEPILOGO_CSV = DATA_DIR / "riepilogo.csv"
WEBSITE_CRAWL_CACHE_FILE = DATA_DIR / "website_crawl_cache.json"

# Percorsi Report PDF (in reports/) — 3 file distinti
PDF_REPORT_FILE = REPORTS_DIR / "Report_Strategico_CNA_Catania_TecnicoLIVE.pdf"
PDF_TERMOIDRAULICA_FILE = REPORTS_DIR / "Report_Termoidraulica_Catania_Provincia_CNA.pdf"
PDF_TOP100_FILE = REPORTS_DIR / "Report_Top100_Termoidraulica_Catania_CEO.pdf"

# Listino Ufficiale TecnicoLIVE (Single Source of Truth)
ANNUAL_DISCOUNT_PCT = 20
CNA_FIRST_YEAR_DISCOUNT_PCT = 50

PRICING_PLANS = {
    "base": {
        "name": "Piano Base",
        "target": "Per ditte individuali e piccoli team",
        "monthly": 169,
        "annual_monthly": 135.20,
        "annual_total": 1622.40,
        "setup_fee": 399,
        "minutes": 150,
    },
    "pro": {
        "name": "Piano Pro",
        "target": "Per team in crescita (Il più scelto)",
        "monthly": 269,
        "annual_monthly": 215.20,
        "annual_total": 2582.40,
        "setup_fee": 599,
        "minutes": 300,
    },
    "business": {
        "name": "Piano Business",
        "target": "Per aziende complesse e reti di installatori",
        "monthly": 369,
        "annual_monthly": 295.20,
        "annual_total": 3542.40,
        "setup_fee": 699,
        "minutes": 500,
    },
}

DEFAULT_ARPU_MONTHLY = PRICING_PLANS["pro"]["monthly"]          # 269 €/mese
DEFAULT_PRO_ANNUAL_MONTHLY = PRICING_PLANS["pro"]["annual_monthly"]  # 215.20 €/mese
DEFAULT_SETUP_FEE_PRO = PRICING_PLANS["pro"]["setup_fee"]       # 599 €

# Identificazione mittente & Opt-Out obbligatorio (AGENTS.md §3B-3C)
SENDER_COMPANY = "Sinergia Rete d'Imprese / TecnicoLIVE"
SENDER_ADDRESS = "Piazza dei Martiri 8, 95131 Catania (CT)"
SENDER_PIVA = "IT06200390877"
SENDER_EMAIL = "info@sinergiainrete.it"
PRIVACY_EMAIL = "privacy@tecnicolive.it"
SENDER_IDENTITY = (
    f"{SENDER_COMPANY} — {SENDER_ADDRESS} — P.IVA {SENDER_PIVA} "
    f"(Partnership Istituzionale CNA Catania)"
)
GDPR_OPTOUT_TEXT = (
    "Se non desidera più ricevere comunicazioni su convenzioni e aggiornamenti normativi "
    "CNA/TecnicoLIVE, risponda CANCELLAMI o scriva a privacy@tecnicolive.it per la "
    "cancellazione immediata da ogni elenco."
)

# Keyword per rilevamento affiliazione CNA
CNA_KEYWORDS = [
    "cna catania",
    "cna sicilia",
    "associat* cna",
    "socio cna",
    "iscritt* cna",
    "confederazione nazionale dell'artigianato",
    "cna unione installazione",
    "cna impiantisti",
    "cna fita",
    "convenzione cna",
]

# Domini web ufficiali CNA
CNA_DOMAINS = [
    "catania.cna.it",
    "cna.it",
    "cnasicilia.com",
    "servizipiu.it",
]

# Pagine secondarie standard per P.IVA e dati societari
SUBPAGES_TO_CHECK = [
    "",
    "contatti",
    "contatti/",
    "chi-siamo",
    "chi-siamo/",
    "servizi",
    "assistenza",
    "privacy-policy",
    "note-legali",
    "legal",
]
