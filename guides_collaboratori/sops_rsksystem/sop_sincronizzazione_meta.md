# SOP RSK-02: Creazione e Sincronizzazione Dinamica delle Custom Audience su Meta

**Obiettivo**: Trasformare una Smart List di RSK System in una Customer List Custom Audience su Facebook e Instagram con aggiornamento dinamico continuo.

---

## Procedura Passo-Passo in RSK System

1. **Apertura del Modulo Ad Manager**:
   - Dalla barra laterale sinistra, clicca su **Marketing** e seleziona **Ad Manager**.
   - Clicca sull'icona dell'ingranaggio in alto a destra (**Ad Manager Settings**).
   - Seleziona la scheda **Meta Audiences**.

2. **Creazione della Custom Audience**:
   - Clicca sul pulsante blu **Create a Custom Audience**.
   - Nella finestra modale, seleziona la sorgente: **Customer List**.
   - Seleziona l'opzione raccomandata: **Use Smart List**.

3. **Selezione della Lista e Configurazione Dinamica (Bivio Critico)**:
   - Dal menu a discesa, seleziona la Smart List creata in precedenza (es. `[AUDIENCE] Preventivi Inviati ma Non Conclusi`).
   - Sotto la voce **Advanced Conditions**, seleziona tassativamente:
     👉 **"Yes, include the dynamic updates"**
   - *Perché questa scelta è fondamentale*: Con la modalità dinamica, ogni volta che un nuovo installatore riceve un preventivo nel CRM, viene aggiunto automaticamente all'audience su Meta entro pochi minuti. Quando accetta il preventivo e diventa cliente, viene rimosso automaticamente dall'audience senza che tu debba fare nulla!

4. **Nomenclatura dell'Audience**:
   - Assegna un nome chiaro e univoco:  
     `Meta Audience - Lead Preventivi Dinamica`
   - Clicca su **Create Audience**.

5. **Verifica dello Stato di Elaborazione**:
   - Nella tabella delle Meta Audiences, la nuova riga mostrerà inizialmente lo stato:  
     🟡 **Not Ready (Processing)**.
   - *Attenzione*: Meta impiega tra i 15 e i 60 minuti per calcolare l'hashing e abbinare i profili. **Non toccare nulla e non tentare di lanciare campagne finché lo stato non cambia in:**  
     🟢 **Ready**.
