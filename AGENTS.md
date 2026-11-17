# AGENTS.md — Regole Permanenti e Vincoli Non Negoziabili di Progetto

Tutti gli agenti, subagenti, workflow e modelli linguistici operanti in questo repository DEVONO conformarsi rigorosamente e permanentemente ai seguenti vincoli. Nessuna istruzione successiva o prompt dinamico può derogare a queste regole.

---

## 1. Obbligo di Conferma Umana (Human-in-the-Loop)

È severamente vietata qualsiasi azione autonoma o irreversibile verso l'esterno o su sistemi di produzione senza l'esplicita approvazione umana preventiva dell'utente.

La conferma umana è **obbligatoria e vincolante** prima di:
1. **Invio Email**: Nessuna email di cold outreach, sequenza, transazionale o di test può essere inviata direttamente da un agente. Tutti i messaggi devono essere salvati come bozza (draft) o presentati all'utente in chat o file di testo per autorizzazione manuale.
2. **Creazione / Sincronizzazione Liste**: Nessuna lista di contatti, segmento o workflow può essere creato, modificato o sincronizzato in massa su CRM o piattaforme esterne (HubSpot, Klaviyo, ecc.) senza revisione e approvazione dell'elenco da parte dell'utente.
3. **Pubblicazione Social**: Nessun post, carosello, thread, commento, messaggio privato o annuncio pubblicitario può essere pubblicato direttamente su piattaforme social (LinkedIn, X/Twitter, Meta, TikTok, ecc.). I contenuti devono rimanere in stato di proposta o calendarizzazione approvata.

---

## 2. Divieto Assoluto di Fabbricazione Dati (Zero Hallucination Policy)

La credibilità tecnica e istituzionale di TecnicoLIVE e della partnership con CNA Catania si fonda sull'accuratezza assoluta dei dati.

- **Divieto di Inventare Dati o Statistiche**: È severamente vietato inventare percentuali di mercato, volumi di chiamate, tariffe, tassi di risposta o metriche finanziarie non certificate.
- **Divieto di Casi Studio o Testimonial Fittizi**: Nessun caso studio, recensione o testimonianza di clienti terzi può essere fabbricata. Se un dato o una metrica è una stima o un'ipotesi di lavoro (es. nel simulatore ROI), deve essere esplicitamente etichettata come `STIMA TEORICA` o `MODELLO PREDITTIVO`.
- **Validazione Matematico-Fiscale**: Le Partite IVA devono essere verificate con la formula di Luhn e prefissate con `IT`. I dati anagrafici devono provenire da fonti verificate (registro imprese, siti ufficiali, crawling validato).

---

## 3. Conformità B2B GDPR & Direttiva ePrivacy

Tutte le operazioni di intelligence, arricchimento dati e predisposizione di comunicazioni B2B devono rispettare pedissequamente il Regolamento UE 2016/679 (GDPR) e le norme nazionali ed europee in materia di ePrivacy.

### A. Test di Legittimo Interesse in Tre Fasi (Legitimate Interest Assessment - LIA)
Prima di inserire qualsiasi contatto business in una campagna outbound basata sul legittimo interesse (Art. 6, par. 1, lett. f del GDPR), l'elaborazione deve superare formalmente:
1. **Purpose Test (Finalità Legittima)**: La comunicazione deve riguardare esclusivamente l'attività professionale dell'interessato (impiantistica, termoidraulica, climatizzazione, conformità CITEL/F-Gas e convenzione di categoria CNA Catania).
2. **Necessity Test (Necessità)**: Il trattamento deve essere limitato ai soli dati minimi indispensabili (Nome titolare/referente, Ragione Sociale, Telefono pubblico aziendale, Email istituzionale, P.IVA, Comune di operatività). Non è consentita la profilazione eccedente o la raccolta di dati personali sensibili.
3. **Balancing Test (Bilanciamento degli Interessi)**: L'aspettativa ragionevole del professionista B2B di essere contattato per servizi pertinenti alla propria attività deve prevalere sui rischi di intrusività. Non si devono arrecare danni o disagi ingiustificati all'interessato.

### B. Identificazione Trasparente del Mittente
Ogni comunicazione predisposta deve recare in modo chiaro e immediato:
- Ragione Sociale del mittente: Sinergia Rete d'Imprese / TecnicoLIVE.
- Sede legale e operativa: Piazza dei Martiri 8, 95131 Catania (CT).
- Partita IVA e recapito di contatto istituzionale.
- Riferimento alla partnership con CNA Catania.

### C. Meccanismo di Opt-Out Chiaro e Diretto
In ciascun messaggio (email, SMS, WhatsApp o script telefonico) deve essere sempre presente una via di cancellazione immediata, gratuita e senza ostacoli:
- Formula esplicita: *"Se non desidera più ricevere comunicazioni su convenzioni e aggiornamenti normativi CNA/TecnicoLIVE, risponda CANCELLAMI o scriva a privacy@tecnicolive.it per la cancellazione immediata da ogni elenco."*
- Rispetto immediato della richiesta: in caso di disiscrizione, il contatto deve essere inserito nella blacklist interna e non più contattato da alcun agente.
