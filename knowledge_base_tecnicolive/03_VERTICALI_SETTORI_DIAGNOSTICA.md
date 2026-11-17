# 🔧 KB-03: Verticali di Settore, Diagnostica & Manuali Tecnici
### Ingegnerizzazione del Linguaggio Tecnico e Decodifica Guasti

---

## 1. La Specializzazione Verticale Termoidraulica
A differenza dei chatbot generici o delle segretarie virtuali non specializzate, TecnicoLIVE è stato **addestrato sul gergo operativo, sulle normative e sui protocolli d'intervento della termoidraulica e dell'impiantistica civile e industriale**.

L'AI non risponde in modo evasivo:
- Comprende la differenza tra pressione a circuito freddo e pressione a circuito caldo.
- Conosce il funzionamento di valvole deviatrici a 3 vie, pressostati di minima e sensori NTC.
- Applica scrupolosamente le normative di legge italiane:
  - **DM 37/08:** Obblighi di sicurezza, conformità impianti e delimitazione delle manovre concesse all'utente.
  - **Regolamento F-Gas:** Procedure per impianti di condizionamento e pompe di calore, test di tenuta circuiti e gestione gas fluorurati (R32, R410A).
  - **Libretto d'Impianto Termico & Bollino Blu (D.P.R. 74/2013):** Scadenze obbligatorie di efficienza energetica e controllo fumi per generatori di calore.

---

## 2. I 6 Settori di Applicazione Tecnica (Master Blueprint v2.4)

| Settore Tecnico | Casistiche e Anomalie Gestite | Comportamento Intelligente dell'AI |
| :--- | :--- | :--- |
| **1. Riscaldamento & Caldaie Civili/Industriali** | Blocchi fiamma, anomalie tiraggio fumi, termosifoni rumorosi/freddi, gocciolamento valvola 3 bar, pulizia scambiatori primari/secondari, termostati smart. | Guida l'utente a leggere il display; se la pressione è sotto 1 bar, illustra come aprire il rubinetto di carico fino a 1.2-1.5 bar; se persiste, registra il codice errore esatto. |
| **2. Climatizzazione & Pompe di Calore** | Blocchi inverter dell'unità esterna, ricariche gas refrigerante R32/R410A, perdite di condensa dall'unità interna, sbrinamento continuo (defrost loop), commutazione estate/inverno. | Distingue tra semplice filtro impolverato e perdita refrigerante o anomalia compressore; avvisa il tecnico del tipo di gas necessario prima dell'uscita. |
| **3. Idraulica Generale, Autoclavi & Scarichi** | Allagamenti da rottura tubi principali, autoclavi che attaccano/staccano continuamente, rottura flessibili, valvole di sicurezza, galleggianti serbatoi, intasamento colonne di scarico. | Fornisce istruzioni di emergenza immediate (chiusura saracinesca generale acqua) e allerta il reperibile; per disotturazioni programma l'intervento con attrezzatura dedicata. |
| **4. Trattamento Acque & Addolcitori** | Promemoria periodico sacchi di sale, rigenerazione resine fallita, acqua calcarea, anomalie impianti a osmosi inversa, filtri defangatori magnetici ostruiti. | Schedula rifornimenti periodici di sale, programma la manutenzione programmata dei filtri e registra la durezza dell'acqua in gradi francesi (°f). |
| **5. Solare Termico & Rinnovabili** | Pressione circuito solare a zero, fluidi termovettori glicolati esausti, sovratemperatura estiva, blocco pompe di circolazione e centraline differenziali. | Comprende schemi a circolazione naturale e forzata, verificando lo stato della centralina elettronica e programmando il rabbocco di glicole. |
| **6. Pronto Intervento & Assistenza Condominiale** | Chiamate da amministratori di condominio per allagamenti cantine, fermi caldaia centralizzata, perdite colonne montanti e rottura autoclavi comuni. | Tracciamento anagrafica amministratore, attribuzione condominio specifico e attivazione del canale prioritario emergenze h24. |

---

## 3. Brand & Manuali Tecnici Appresi (+500 Modelli Integrati)

L'archivio RAG (Retrieval-Augmented Generation) di TecnicoLIVE include la documentazione ufficiale di installazione, uso e manutenzione dei principali produttori:

### 🔹 Vaillant
- **ecoTEC Plus / Pro / Exclusive:**
  - *F.28:* Mancata accensione (gas assente, elettrodo accensione difettoso).
  - *F.29:* Spegnimento fiamma durante il funzionamento.
  - *F.22:* Mancanza d'acqua (pressione inferiore a 0.6 bar).
  - *F.75:* Mancato riconoscimento salto di pressione all'avvio pompa.

### 🔹 Baxi
- **Luna 3, Duo-tec Compact, Platinum:**
  - *E01:* Blocco mancata accensione fiamma.
  - *E03:* Intervento termostato fumi o pressostato fumi.
  - *E10:* Mancato consenso pressostato idraulico (pressione insufficiente).
  - *E35:* Fiamma parassita (anomalia rivelazione fiamma).

### 🔹 Ariston
- **Clas One, Genus One, Alteas:**
  - *Errore 501:* Assenza di fiamma.
  - *Errore 108:* Pressione impianto insufficiente (aprire rubinetto di carico).
  - *Errore 607:* Pressostato fumi scattato prima dell'accensione del ventilatore.
  - *Errore 305:* Errore scheda logica principale.

### 🔹 Buderus / Bosch / Junkers
- **Logamax, Condens 2300/5000, Cerapur:**
  - *EA:* Mancata rilevazione corrente di ionizzazione / mancata accensione.
  - *CE:* Pressione circuito idraulico troppo bassa.
  - *C6:* Ventilatore o pressostato fumi non funzionante.

### 🔹 Immergas
- **Victrix Tera, Victrix Maior:**
  - *Codice 01:* Blocco mancata accensione.
  - *Codice 10:* Pressione impianto insufficiente.
  - *Codice 27:* Circolazione acqua insufficiente o pompa bloccata.

### 🔹 Daikin
- **Monosplit/Multisplit & Pompe di Calore Altherma:**
  - *A5:* Controllo alta pressione unità interna / protezione scambiatore.
  - *U4:* Errore comunicazione tra unità interna ed esterna.
  - *L5:* Sovracorrente al compressore inverter.
  - *H9:* Anomalia sensore temperatura aria esterna.

---

## 4. Il Valore della Pre-Diagnosi per l'Officina Mobile
Grazie a questo database, il tecnico non sale più sul furgone alla cieca:
- Riceve su WhatsApp: *"Chiamata Sig.ri Bianchi - Caldaia Vaillant ecoTEC Plus con Errore F.28. Il cliente ha verificato che il fornello del gas funziona regolarmente. Probabile elettrodo o valvola gas. Suggerito ricambio codice 0020025294."*
- Il tecnico carica il pezzo a magazzino e risolve l'intervento **al primo colpo**, abbattendo dell'**80% le doppie uscite a vuoto**.
