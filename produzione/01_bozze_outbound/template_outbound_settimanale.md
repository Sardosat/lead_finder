# Modello Scheda Lavoro: Campagna Outbound Settimanale

**Settimana**: `[Numero Settimana / Date]`  
**Comune / Territorio Target**: `[es. Paternò / Belpasso / Acireale]`  
**Settore / Nicchia**: `[es. Caldaie & Termoidraulica]`  
**Collaboratore Assegnato**: `[Nome Collaboratore]`

---

## 1. Selezione Contatti dal Database Locale

- **File Sorgente**: `data/campagna_outbound_tecnicolive.csv`
- **Numero Contatti Filtrati**: `[Numero, es. 25]`
- **Stato CNA Prevalente**: `[Associato Rilevato (Sconto 15%) / Non Associato (Sconto Quota 1° Anno)]`

---

## 2. Script Telefonico di Apertura Predisposto

```text
Operatore: "Buongiorno [Nome Titolare / Ragione Sociale], la contatto da TecnicoLIVE in merito alla convenzione ufficiale con CNA Catania per le aziende impiantistiche del comune di [Comune].
Sappiamo che in questo periodo siete spesso in cantiere con le mani occupate e molte chiamate di nuovi clienti finiscono senza risposta mentre siete sui furgoni.
Con la convenzione CNA Catania vi attiviamo l'assistente vocale AI che risponde H24 ai vostri clienti, fa la pre-diagnosi del guasto e vi invia la scheda su WhatsApp, con canone agevolato di categoria e [sconto convenzione per soci / quota primo anno d'iscrizione a CNA scontata per chi non è ancora socio].
Avete 5 minuti oggi alle 17:00 per fare una prova live chiamando il nostro numero test?"
```

---

## 3. Messaggio WhatsApp di Follow-Up / Scaldamento

```text
Ciao [Nome], ti scrivo da TecnicoLIVE (partner ufficiale CNA Catania).
Quante chiamate di nuovi clienti perdi ogni settimana mentre sei sotto una caldaia o in cantiere con le mani occupate?
Il nostro assistente vocale AI risponde per te in 3 secondi, riconosce il guasto (Vaillant, Buderus, Baxi, Bosch) e ti prenota l'intervento direttamente su WhatsApp.
👉 Ascolta come risponde con la voce di un tecnico vero: https://www.tecnicolive.it
In convenzione CNA hai 7 giorni di prova gratuita senza impegno e la quota del 1° anno scontata. Ti lascio il link per testarlo?

(Rispondi CANCELLAMI per non ricevere ulteriori aggiornamenti)
```

---

## 4. Spazio Approvazione QA & Supervisore

- [ ] Controllo QA superato (`STATO: VERIFICATO QA`)
- [ ] Approvazione Supervisore Umano rilasciata
