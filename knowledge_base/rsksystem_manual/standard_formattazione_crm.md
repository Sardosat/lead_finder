# Standard di Formattazione e Normalizzazione CRM — RSK System

Questo documento stabilisce le regole tecniche obbligatorie che ogni collaboratore e agente deve seguire prima di importare o sincronizzare qualsiasi contatto nel CRM di RSK System.

---

## 1. Regole di Normalizzazione Campi

| Campo CRM | Formato Obbligatorio | Esempio Corretto | Errore Grave da Evitare |
|---|---|---|---|
| **Email** | Tutto minuscolo, senza spazi iniziali/finali | `mario.rossi@termoidraulica.it` | `Mario.Rossi@Azienda.IT `, spazi vuoti |
| **Telefono** | Standard internazionale E.164 (`+39` per l'Italia) | `+393331234567` o `+39095123456` | `333 1234567`, `095/123456`, numeri senza `+39` |
| **First Name** | Nome proprio del titolare o referente | `Mario` | Lasciare vuoto o inserire la ragione sociale |
| **Last Name** | Cognome del titolare o referente | `Rossi` | Inserito insieme al nome nello stesso campo |
| **Company Name** | Ragione sociale estesa pulita | `Clima Comfort S.r.l.` | Tutto maiuscolo sgrammaticato o abbreviazioni oscure |
| **Country** | Codice ISO a 2 lettere maiuscolo | `IT` | `Italia`, `Italy`, `ITA` |
| **Postal Code** | CAP a 5 cifre con zero iniziale preservato | `95131`, `00100` | Troncamento dello zero iniziale (es. `100`) |
| **City** | Nome del comune con iniziale maiuscola | `Acireale`, `Catania`, `Paternò` | `ct`, `catania (CT)` disomogeneo |

---

## 2. Nomenclatura Standard dei Tag in RSK System

Tutti i contatti devono essere etichettati tramite tag strutturati per alimentare le **Smart Lists dinamiche**:

- `Target: Termoidraulica` / `Target: Caldaie` / `Target: Climatizzazione` / `Target: Elettrico`
- `Territorio: Catania Metropolitana` / `Territorio: Distretto Acese` / `Territorio: Polo Ovest`
- `Stato CNA: Associato Rilevato` / `Stato CNA: Target Tesseramento`
- `Pipeline: Lead Freddo` / `Pipeline: Contatto Avviato` / `Pipeline: Preventivo Inviato` / `Pipeline: Cliente Attivo`
- `Origine: Scraping Diretto` / `Origine: Meta Ads Lead` / `Origine: Inbound DM Social`

---

## 3. Gestione della Soglia Minima per Meta Ads

- Meta non avvia l'erogazione pubblicitaria se la Customer List conta meno di **100 profili attivi matched**.
- Se un segmento locale (es. solo comune di Acireale) ha meno di 100 contatti, unirlo con il segmento provinciale più vicino per garantire la densità minima richiesta dall'algoritmo.
