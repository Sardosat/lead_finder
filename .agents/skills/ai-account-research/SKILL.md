---
name: ai-account-research
description: "Agente di ricerca qualitativa web (stile Claygent) per estrarre dai siti marchi trattati (Buderus, Vaillant, Baxi), reperibilità H24, certificazioni F-Gas/CITEL e dimensione ditta."
metadata:
  author: TecnicoLIVE & Clay Intelligence
  version: 1.0.0
---

# AI Account Research (Il 'Claygent' di TecnicoLIVE)

La skill **ai-account-research** sostituisce l'analisi manuale delle schede aziendali, scansionando semanticamente il testo del sito web o della presenza online dell'installatore.

## Questionario Qualitativo Eseguito su Ogni Account

1. **Marchi di Caldaie Trattati**:
   - Cerca citazioni esplicite di: `Vaillant`, `Buderus`, `Baxi`, `Bosch`, `Ariston`, `Ferroli`, `Beretta`, `Immergas`.
   - Identifica se la ditta è Centro Assistenza Tecnica autorizzato (CAT).
2. **Marchi di Climatizzazione & Pompe di Calore**:
   - Cerca citazioni di: `Daikin`, `Mitsubishi Electric`, `Panasonic`, `Samsung`.
3. **Livello di Servizio e Reperibilità**:
   - Cerca parole chiave come `H24`, `pronto intervento`, `reperibilità festivi`, `sabato mattina`.
   - Se presente, genera il gancio sul riposo del tecnico ("basta tenere il telefono sul comodino di notte").
4. **Certificazioni e Adempimenti**:
   - Rileva menzioni di patentino `F-Gas`, `Bollino Blu` e caricamento telematico `CITEL Sicilia`.
