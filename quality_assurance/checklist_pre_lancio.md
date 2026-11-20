# Checklist Operativa Pre-Lancio (Anti-Errore)

**Documento di controllo obbligatorio da compilare per ogni campagna Meta Ads, lista contatti o blocco di post social.**  
*Riferimento vincolante: Manuale Operativo RSK System Sezione 10 & AGENTS.md*

---

## 1. Dati della Revisione

- **Data della Verifica**: `AAAA-MM-GG`
- **Oggetto del Controllo**: `[Titolo Campagna / Post / Lista Contatti]`
- **Collaboratore che ha preparato la bozza**: `[Nome Collaboratore]`
- **File di Riferimento in `/produzione`**: `[Percorso File]`

---

## 2. Tabella di Verifica dei 10 Punti di Controllo

| # | Punto di Controllo | Requisito da Verificare | Esito (SI / NO) | Note del QA Controller |
|---|---|---|---|---|
| **1** | **Connessione Account Meta** | L'account Meta e l'Ad Account sono attivi e connessi in *Settings > Integrations* di RSK System. | [ ] | |
| **2** | **Accettazione TOS Meta** | I termini *Meta Custom Audience TOS* risultano formalmente accettati a livello amministratore. | [ ] | |
| **3** | **Normalizzazione E.164 Telefono** | Tutti i numeri nel database o nella lista hanno il prefisso internazionale `+39` (es. `+393331234567`). | [ ] | |
| **4** | **Normalizzazione Email & P.IVA** | Email in minuscolo senza spazi; Partita IVA validata col codice di controllo di Luhn e prefisso `IT`. | [ ] | |
| **5** | **Audience Dinamica & Stato Ready** | L'audience in RSK System è impostata come *Dinamica* ed è in stato 🟢 **Ready** (non *Processing*). | [ ] | |
| **6** | **Esclusione Clienti Attivi (Tassativa)** | Nel gruppo inserzioni (Ad Set) è impostata l'esclusione esplicita della lista `Clienti Già Acquisiti`. | [ ] | |
| **7** | **Limiti Caratteri Titolo & Testo** | Titolo dell'annuncio ≤ 40 caratteri; messaggio principale con promessa nei primi 125 caratteri. | [ ] | |
| **8** | **Audit Linguistico Brand Voice** | Assenza totale di parole vietate (*delve, olistico, rivoluzione, chatbot, landscape*); tono di cantiere. | [ ] | |
| **9** | **Formato Grafico & Watermark** | Creatività nel formato corretto (1:1 o 4:5), meno del 20% di testo, presenza del logo TecnicoLIVE/CNA. | [ ] | |
| **10** | **Formula di Opt-Out & Human-in-the-Loop** | Presente clausola di cancellazione B2B GDPR; la campagna o il post è salvato in **Bozza** in attesa di approvazione. | [ ] | |

---

## 3. Esito Finale del QA Controller

- [ ] **APPROVATO (Tutti i punti sono SI)**: La bozza può essere inoltrata ai supervisori per l'autorizzazione finale.
- [ ] **RESPINTO (Almeno un punto è NO)**: La bozza deve essere corretta dal collaboratore seguendo le note sopra indicate.
