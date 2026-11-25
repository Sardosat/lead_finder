# Modello Scheda Lavoro: Campagna Outbound Settimanale

**Settimana**: `[Numero Settimana / Date]`  
**Comune / Territorio Target**: `[es. Paternò / Belpasso / Acireale]`  
**Settore / Nicchia**: `[es. Caldaie & Termoidraulica]`  
**Collaboratore Assegnato**: `[Nome Collaboratore]`

---

## 1. Selezione Contatti dal Database Locale

- **File Sorgente**: `data/campagna_outbound_tecnicolive.csv`
- **Numero Contatti Filtrati**: `[Numero, es. 25]`
- **Stato CNA Prevalente**: `[Associato Rilevato / Non Associato (Associazione CNA 50% 1° Anno)]`

---

## 2. Script Telefonico di Apertura Predisposto

```text
Operatore: "Buongiorno [Nome Titolare / Ragione Sociale], la contatto da Sinergia Rete d'Imprese / TecnicoLIVE (Piazza dei Martiri 8, Catania) in merito alla convenzione ufficiale con CNA Catania per le aziende impiantistiche del comune di [Comune].
Sappiamo che in questo periodo siete spesso in cantiere con le mani occupate e molte chiamate di nuovi clienti finiscono senza risposta mentre siete sui furgoni.
Con la convenzione CNA Catania attiviamo l'assistente vocale AI che risponde H24 ai vostri clienti con chiamate simultanee illimitate, fa la pre-diagnosi del guasto e vi invia la scheda su WhatsApp; per chi non è ancora socio sblocchiamo anche l'associazione a CNA Catania al 50% per tutto il primo anno.
Avete 5 minuti oggi alle 17:00 per fare una prova live chiamando il nostro numero test +39 095 342 0411?"
```

---

## 3. Messaggio WhatsApp di Follow-Up / Scaldamento

```text
Ciao [Nome], ti scrivo da TecnicoLIVE (Sinergia Rete d'Imprese, partner ufficiale CNA Catania).
Quante chiamate di nuovi clienti perdi ogni settimana mentre sei sotto una caldaia o in cantiere con le mani occupate?
Il nostro assistente vocale AI risponde per te in 3 secondi, riconosce il guasto (Vaillant, Buderus, Baxi, Bosch) e ti prenota l'intervento direttamente su WhatsApp.
👉 Ascolta come risponde chiamando il numero test +39 095 342 0411 o su: https://www.tecnicolive.it
Con la convenzione CNA Catania hai anche l'iscrizione a CNA al 50% per tutto il primo anno! Ti lascio i dettagli dei piani (a partire da 169€/mese)?

—
Sinergia Rete d'Imprese / TecnicoLIVE — Piazza dei Martiri 8, 95131 Catania (CT) — P.IVA IT06200390877.
Se non desidera più ricevere comunicazioni su convenzioni e aggiornamenti normativi CNA/TecnicoLIVE, risponda CANCELLAMI o scriva a privacy@tecnicolive.it per la cancellazione immediata da ogni elenco.
```

---

## 4. Spazio Approvazione QA & Supervisore

- [ ] Controllo QA superato (`STATO: VERIFICATO QA`)
- [ ] Approvazione Supervisore Umano rilasciata
