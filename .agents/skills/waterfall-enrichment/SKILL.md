---
name: waterfall-enrichment
description: "Arricchimento contatti a cascata multi-provider (stile Clay.com) per massimizzare il Match Rate di numeri cellulari E.164 (+39), email aziendali, PEC e Partite IVA validate con Luhn."
metadata:
  author: TecnicoLIVE & Clay Intelligence
  version: 1.0.0
---

# Waterfall Enrichment — TecnicoLIVE GTM Intelligence

La skill **waterfall-enrichment** implementa la sequenza di arricchimento a cascata ideata da Clay.com, adattata specificamente al tessuto imprenditoriale dell'impiantistica e termoidraulica italiana.

## Principio di Funzionamento della Cascata (Waterfall)

Invece di affidarsi a un unico database o a un solo scraper, la cascata interroga più sorgenti sequenzialmente:
1. **Livello 1 (Sito Web Aziendale / Crawl4AI)**: Estrazione diretta di JSON-LD, metadati OpenGraph, footer e pagina `/contatti` per identificare telefoni diretti, P.IVA e email.
2. **Livello 2 (Google Business Profile / Local Pack)**: Recupero del numero telefonico pubblico d'emergenza, orari di apertura e indirizzo completo con CAP.
3. **Livello 3 (PagineGialle & Directory Professionali)**: Estrazione dati camerali, categoria ATECO e ragione sociale registrata.
4. **Livello 4 (Normalizzazione & Verifica Crittografica)**:
   - Numeri telefonici formattati obbligatoriamente nello standard **E.164** (`+39...`).
   - Identificazione del tipo di numero: mobile (`3xx`) per WhatsApp vs fisso (`0xx`).
   - Partita IVA validata matematicamente col checksum di Luhn e prefissata con `IT`.

## Risultato Atteso
- Match Rate per Meta Ads superiore all'**80%**.
- Zero scarti di formattazione durante il caricamento su RSK System.
