# Lead Intelligence Engine IT/EU • TecnicoLIVE • RSK System • MonetizeLab

Piattaforma B2B modulare di **Lead Generation, Arricchimento a 3 Livelli stile Clay.com (adattato a Italia & Europa), Conformità B2B GDPR (LIA + Blocco PEC + RPO) e Routing Multi-Prodotto** progettata per le PMI italiane ed europee.

---

## 🎯 Architettura Ecosistema & Monetizzazione

1. **Lead Intelligence Engine (`engine/`, `api/`)** — Prodotto di acquisizione B2B locale ad alta copertura (Google Places/Serper + ISTAT Geo-Lock + VIES UE + Tech Audit + Gemini 2.5 Flash + Openapi.com).
2. **Router Automatico sui 3 Prodotti dell'Ecosistema**:
   - **`monetizelab.online`**: per **Marketing Agency, Web Agency e Content Creator** (ATECO `73.11`, `73.12`, `74.10`, `59.11`).
   - **`tecnicolive.it`**: per **Termoidraulici, Elettricisti, Caldaisti e Installatori Impianti** (ATECO `43.21`, `43.22`, `43.29`) con convenzione **CNA Catania al 50% per il 1° anno** e listino ufficiale (Base 169€ + 399€ setup, Pro 269€ + 599€ setup, Business 369€ + 699€ setup, `-20%` annuale).
   - **`rsksystem.com`**: per tutte le altre **PMI italiane ed europee B2B/B2C** (CRM sovrano, Smart Lists, WhatsApp/Email automation).

---

## 🛠️ Setup Ambiente & Variabili `.env` (Python >= 3.10)

### 1. Virtualenv
```bash
# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

### 2. Configurazione Chiavi API (`.env`)
Copia `.env.example` in `.env` (file ignorato da Git) e inserisci le chiavi necessarie:
- `SERPER_API_KEY` o `GOOGLE_PLACES_API_KEY` (Seed Discovery locale)
- `GEMINI_API_KEY` (Livello 2 AI Context `gemini-2.5-flash` con Structured Outputs)
- `OPENAPI_API_KEY` / `OPENAPI_USERNAME` / `OPENAPI_TOKEN` (Livello 3 Dati Camerali `company.openapi.com`)
- `SUPABASE_URL`, `SUPABASE_KEY`, `RSK_WEBHOOK_URL` (Storage multi-tenant & Webhook)

---

## 🚀 Comandi Principali

### Motore Multi-Prodotto IT/EU (`engine/` + `api/`)
```bash
# Demo end-to-end (Geo-Lock vs Clay, Product Router, LIA GDPR, PEC Block, Webhook dry-run)
python main.py --engine-demo

# Verifica live gratuita P.IVA su VIES Commissione Europea
python main.py --vies IT06200390877

# Livello 1 Tech Audit + verifica DNS MX su un dominio aziendale
python main.py --tech-audit https://www.tecnicolive.it

# Livello 3 Dati Camerali italiani via Openapi.com (con budget cap e cache)
python main.py --openapi-check IT06200390877

# Avvio API REST FastAPI (per frontend Next.js / SaaS)
uvicorn api.server:app --reload
```

### Dashboard Interattiva Streamlit (4 Tab)
```bash
streamlit run app.py
```

### Bonifica Dataset, Report PDF & Test
```bash
# Bonifica, deduplica, normalizzazione E.164, crawl live siti reali e sync CSV/Excel
python main.py --clean
python main.py --clean --crawl

# Generazione report PDF (strategico, termoidraulica, top100, all)
python main.py --pdf all

# Suite test completa
pytest -v
```

---

## 📁 Struttura ad Albero del Monorepo

```text
LEAD_FINDER/
├── api/                               # Backend REST FastAPI per SaaS / Next.js
│   └── server.py
├── campaigns/                         # Playbook configurabili multi-settore (ATECO/ISTAT)
│   ├── 01_impiantisti_tecnicolive.json
│   ├── 02_agenzie_monetizelab.json
│   └── 03_pmi_generiche_rsksystem.json
├── engine/                            # Core SaaS Multi-Settore IT/EU (stile Clay locale)
│   ├── schemas/                       # Modelli Pydantic canonici (LeadRecord, CampaignConfig, LIAAssessment)
│   ├── routing/                       # Router ecosistema (monetizelab.online / rsksystem.com / tecnicolive.it)
│   ├── compliance/                    # Motore GDPR LIA 3 fasi, blocco PEC, avviso RPO, suppression list
│   ├── connectors/                    # Seed Places/Serper (Geo-Lock), VIES UE, Openapi.com IT-start/advanced
│   ├── enrichment/                    # L1 Tech Audit + MX, L2 Gemini 2.5 Flash Structured JSON, Pipeline Runner
│   └── exporters/                     # Export CSV canonico & Webhook RSK/GHL/n8n (Human-in-the-Loop dry-run)
├── supabase/
│   └── migrations/001_initial_schema.sql # Schema PostgreSQL multi-tenant con RLS & LIA trail
├── src/                               # Pipeline verticale Catania & generatori PDF/Excel
├── data/                              # Dataset operativi puliti, cache API e suppression_list.csv
├── exports_excel/                     # Workbook Excel formattati
├── reports/                           # Report direzionali PDF (3 documenti distinti)
├── tests/                             # Suite test pytest completa
├── app.py                             # Dashboard Streamlit 4 tab
├── main.py                            # CLI unificata
└── AGENTS.md                          # Vincoli permanenti (Human-in-the-Loop, Zero Hallucination, GDPR)
```
