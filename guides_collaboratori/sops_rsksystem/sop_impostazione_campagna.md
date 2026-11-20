# SOP RSK-03: Impostazione Campagna Meta Ads e Regola delle Esclusioni

**Obiettivo**: Creare un gruppo inserzioni (Ad Set) su RSK System applicando correttamente il pubblico personalizzato e impostando l'esclusione obbligatoria dei clienti già acquisiti.

---

## Procedura Passo-Passo in RSK System

1. **Creazione della Campagna**:
   - Vai su **Marketing > Ad Manager > Campaigns**.
   - Clicca sul pulsante **Create Campaign**.
   - Seleziona l'obiettivo approvato dai supervisori:
     - Per raccogliere contatti: seleziona **Lead Generation**.
     - Per generare conversazioni WhatsApp: seleziona **Messages / Sales**.
   - Assegna il nome secondo la nomenclatura standard:  
     `[SCENARIO 1] Retargeting Preventivi Caldaisti Catania - Q1 2026`

2. **Configurazione dell'Ad Set (Gruppo di Inserzioni)**:
   - Clicca a livello di Ad Set e scorri fino alla sezione **Audience Controls**.
   - Individua il blocco **Intended Audience** e clicca sul tab **Retargeting**.
   - Nel menu a tendina *Select Retargeting Audience*, scegli la lista sincronizzata in precedenza (es. `Meta Audience - Lead Preventivi Dinamica`).
   - Assicurati che lo stato sia 🟢 **Ready**.

3. **Applicazione Tassativa dell'Esclusione (Regola Anti-Spreco)**:
   - Subito sotto il blocco di inclusione, clicca sul link **Exclude Audience**.
   - Nel menu a tendina delle esclusioni, seleziona la lista dei clienti attivi:  
     👉 `Meta Audience - Clienti Già Acquisiti` (o `[ESCLUSIONE] Clienti Attivi 2026`).
   - *Controllo obbligatorio*: Se questa voce non è presente, **fermati subito** e chiedi al controller QA! Senza questa esclusione, mostrerai inserzioni a pagamento a persone che pagano già il canone mensile di TecnicoLIVE.

4. **Caricamento della Creatività e dei Testi**:
   - Passa a livello di **Ad (Inserzione)**.
   - Copia e incolla il testo principale (Primary Text) e il titolo (Headline) approvati dall'agente Content Creator e verificati dal QA Controller.
   - Carica l'immagine o il video nel formato corretto (1:1 o 4:5 per feed mobile).
   - Imposta il link di destinazione con i parametri UTM standard.

5. **Salvataggio in Bozza**:
   - Clicca su **Save Draft**.
   - **NON cliccare su "Publish / Lancia"**: compila la riga di richiesta nel file `quality_assurance/registro_revisioni.md` e mostra la campagna al supervisore per il via libera definitivo.
