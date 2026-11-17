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
OUTPUT_CSV_ENRICHED = DATA_DIR / "leads_arricchiti.csv"
OUTPUT_RIEPILOGO_CSV = DATA_DIR / "riepilogo.csv"

# Percorso Report PDF (in reports/)
PDF_REPORT_FILE = REPORTS_DIR / "Report_Strategico_CNA_Catania_TecnicoLIVE.pdf"

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
    "privacy-policy",
    "note-legali",
    "legal",
]
