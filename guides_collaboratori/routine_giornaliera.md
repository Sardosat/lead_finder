# Routine Operativa Giornaliera per i Collaboratori

Questa guida descrive le attività quotidiane da svolgere dal lunedì al venerdì, divise tra sessione mattutina e sessione pomeridiana.

---

## 🌅 Mattina (09:00 - 13:00)

### 1. Check-In & Monitoraggio Inbound (09:00 - 09:30)
- [ ] Accedi a **RSK System** nel sub-account aziendale di TecnicoLIVE.
- [ ] Controlla la sezione **Conversations**: ci sono nuovi messaggi WhatsApp o richieste di contatto arrivate nella notte?
- [ ] Controlla la pagina Facebook e Instagram: ci sono commenti sotto gli annunci o i post organici?
- [ ] Se ci sono commenti o messaggi: apri il file `guides_collaboratori/templates_pronti/risposte_commenti_e_dm.md` e rispondi applicando la risposta approvata entro 15 minuti.

### 2. Creazione del Contenuto del Giorno (09:30 - 12:00)
- [ ] Apri il calendario settimanale in `produzione/02_bozze_social/` per vedere cosa è previsto per oggi (es. post su Blocco F28 o video su chiamate perse).
- [ ] Interroga l'agente **Content Creator**: chiedigli di redigere la bozza per il canale previsto (Facebook, Instagram o LinkedIn).
- [ ] Interroga l'agente **Visual Designer**: richiedi la specifica grafica per il formato corretto (1:1 o 4:5).
- [ ] Se necessario, apri Canva e componi la grafica seguendo alla lettera i colori e le posizioni fornite dall'agente.
- [ ] Salva il testo e l'anteprima grafica in `produzione/02_bozze_social/`.

### 3. Gestione e Arricchimento Lead (12:00 - 13:00)
- [ ] Apri la Dashboard su `http://localhost:8501` e consulta il **Tab 1 (Lead Finder)**.
- [ ] Filtra un comune target (es. Acireale o Paternò) e verifica le ditte da contattare con l'agente **Lead Hunter**.
- [ ] Prepara la lista di bozze di contatto per il pomeriggio.

---

## 🌇 Pomeriggio (14:30 - 18:00)

### 4. Controllo Qualità Obbligatorio (14:30 - 15:30)
- [ ] Prendi la bozza del contenuto creata al mattino o la lista lead.
- [ ] Sottoponila all'agente **QA Operational Controller**.
- [ ] L'agente controllerà: lunghezze caratteri, assenza di parole vietate, formattazione E.164 dei numeri, rispetto dei formati.
- [ ] Se l'agente segnala un errore, correggilo subito fino a ottenere l'approvazione **`STATO: VERIFICATO QA`**.

### 5. Presentazione ai Supervisori per Approvazione (15:30 - 16:30)
- [ ] Mostra ai supervisori di progetto la scheda riassuntiva del contenuto o della campagna pronta.
- [ ] Attendi il via libera formale ("Approvato").
- [ ] Una volta approvato, registra l'attività nel file `quality_assurance/registro_revisioni.md`.

### 6. Caricamento in Bozza su RSK System o Social (16:30 - 17:30)
- [ ] Carica il post approvato nello strumento di pianificazione di RSK System o programma l'inserzione Meta Ads a livello di bozza.
- [ ] Verifica che l'orario di pubblicazione sia conforme al calendario (orari raccomandati per installatori: **12:30 - 14:00** o **18:00 - 19:30**).

### 7. Check-Out Giornaliero (17:30 - 18:00)
- [ ] Salva tutti i file aperti.
- [ ] Segna le attività completate sul foglio di lavoro.
- [ ] Chiudi le sessioni in sicurezza.
