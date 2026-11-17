# Lead Finder TecnicoLIVE & CNA Catania

Sistema avanzato di **Lead Generation, Estrazione Partita IVA e Verifica Affiliazione a CNA Catania** progettato per le 4 nicchie impiantistiche di Catania e provincia:
1. **HVAC, Caldaisti, Climatizzazione e Riscaldamento**
2. **Termoidraulica e Idraulici**
3. **Impianti Elettrici ed Elettricisti**
4. **Impiantistica Generale e Grandi Appalti**

---

## 🎯 Obiettivo Strategico

- **Se il lead è già socio CNA Catania**: proporre l'assistente vocale IA **TecnicoLIVE** con la convenzione e lo sconto esclusivo riservato ai soci.
- **Se il lead NON è socio CNA Catania**: sbloccare la doppia vendita: *"Ti associamo a CNA Catania per farti ottenere la convenzione TecnicoLIVE + tutti i benefici sindacali e legali dell'associazione"*.

---

## 🚀 Comandi Principali

Attiva l'ambiente virtuale:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 1. Ricerca Attiva di NUOVI Lead (`--discover`)
Trova nuove imprese a Catania e provincia nei 4 settori, estrae la Partita IVA, deduplica rispetto alle lead già presenti e controlla l'affiliazione CNA:

```powershell
# Cerca fino a 10 nuovi lead per ciascun settore (default su Catania)
python main.py --discover

# Cerca su un comune specifico della provincia (es. Acireale, Misterbianco, Giarre, Mascalucia)
python main.py --discover --city acireale --max-per-sector 10

# Scandaglia a tappeto TUTTI i principali comuni della Città Metropolitana di Catania
python main.py --discover --all-cities --max-per-sector 10
```

### 2. Generazione del Report Strategico in PDF (`--pdf`)
Genera il documento PDF formattato con tutte le metriche, tabelle e grafici pronti per la stampa o l'invio direzionale:

```powershell
python main.py --pdf
```

### 3. Verifica e Arricchimento dei Lead Esistenti
Elabora i file CSV originali presenti in `CSV_Leads/`:

```powershell
# Elaborazione completa di tutte le lead
python main.py

# Test pilota rapido (es. prime 5 lead)
python main.py --limit 5
```

---

## 📁 Struttura e Albero delle Cartelle

Il progetto è organizzato con una separazione netta tra file CSV di lavoro (apribili nativamente nell'editor), file Excel formattati e report PDF:

```
lead_finder/
├── data/                         # File CSV di lavoro (apribili direttamente nell'editor)
│   ├── tutte_le_lead.csv         # 124 lead decontaminate (solo Italia/Catania)
│   ├── target_tesseramento_cna.csv # 64 aziende con P.IVA pronte per la vendita combinata
│   ├── associati_rilevati.csv    # Aziende con affiliazione CNA accertata
│   ├── nuove_lead_scoperte.csv   # Nuove aziende scoperte dal motore di ricerca
│   ├── campagna_outbound_tecnicolive.csv # Tabella con pitch commerciale personalizzato per chiamata
│   ├── richiesta_verifica_cna.csv # Foglio di spunta pulito per l'Ufficio Soci CNA
│   └── riepilogo.csv             # Cruscotto statistiche
├── exports_excel/                # TUTTI i file Excel (.xlsx) formattati con stili e colori
│   ├── leads_cna_dashboard.xlsx  # Dashboard consolidata a fogli multipli
│   ├── richiesta_verifica_cna.xlsx # Tabella per CNA Catania
│   └── nuove_lead_scoperte.xlsx  # Nuove lead estratte
├── reports/                      # Reportistica direzionale (PDF)
│   └── Report_Strategico_CNA_Catania_TecnicoLIVE.pdf
├── CSV_Leads/                    # File CSV sorgenti puliti (filtrati da numeri esteri/maltesi)
├── src/                          # Codice sorgente Python modulare
└── knowledge_base_tecnicolive/   # Documentazione e KB ufficiale TecnicoLIVE
```
