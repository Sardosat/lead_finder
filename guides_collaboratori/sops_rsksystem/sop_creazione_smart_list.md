# SOP RSK-01: Creazione e Gestione delle Smart Lists nel CRM

**Obiettivo**: Creare segmenti di contatti ordinati, puliti e pronti per essere sincronizzati con Meta Ads o usati per le campagne outbound.

---

## Procedura Passo-Passo in RSK System

1. **Accesso alla Sezione Contatti**:
   - Dalla barra laterale sinistra di RSK System, clicca sull'icona **Contacts**.
   - Clicca in alto sulla scheda **Smart Lists**.

2. **Impostazione dei Filtri Avanzati**:
   - Clicca sul pulsante **More Filters** (sul lato destro della tabella).
   - Nel pannello laterale che si apre, seleziona i filtri desiderati:
     - *Per Segmentare per Settore*: Seleziona `Tag` -> `Is` -> Scegli (es. `Target: Caldaie`).
     - *Per Segmentare per Stato CNA*: Seleziona `Tag` -> `Is` -> Scegli `Stato CNA: Target Tesseramento`.
     - *Per Segmentare per Stato Trattativa*: Seleziona `Pipeline Stage` -> `Is` -> Scegli `Preventivo Inviato`.
     - *Per Escludere i Clienti*: Aggiungi condizione `Tag` -> `Is Not` -> `Cliente Attivo`.

3. **Verifica della Qualità dei Dati**:
   - Scorri le righe del segmento filtrato:
     - I numeri hanno tutti il prefisso `+39`?
     - I nomi e cognomi sono separati e non contengono simboli strani?
   - Se riscontri numeri privi di prefisso, seleziona tutti i contatti, clicca sull'icona delle azioni massive e seleziona **Format Phone Numbers** aggiungendo il prefisso `+39`.

4. **Salvataggio della Smart List**:
   - Clicca sul pulsante **Save as Smart List** in basso a destra.
   - Inserisci un nome conforme allo standard:
     - Esempio 1: `[AUDIENCE] Preventivi Inviati ma Non Conclusi`
     - Esempio 2: `[AUDIENCE] Target Tesseramento CNA Catania`
     - Esempio 3: `[ESCLUSIONE] Clienti Attivi 2026`
   - Clicca su **Save**.

5. **Risultato**: La nuova Smart List compare come tab fisso in alto nella sezione contatti e si aggiornerà automaticamente ogni volta che un contatto riceverà o perderà i tag specificati.
