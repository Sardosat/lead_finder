1. Il Core Business: cosa vende davvero questo tool?
Il core business non è "un foglio di calcolo dove smanettare con 100 colonne".

Il core business è trasformare fonti frammentate locali (Google Maps, siti web, PagineGialle/directory, dati pubblici/camerali) in liste di aziende verificabili, qualificate dall'AI e pronte per l'acquisizione commerciale.

Le tre promesse di valore che lo fanno pagare subito:

Copertura locale reale (Sud e PMI non-LinkedIn): trova l'azienda anche se non ha LinkedIn, ma ha un profilo Google Business, un sito vetrina, una PEC o una partita IVA pubblica.

Qualificazione AI sul contesto (non solo "dati anagrafici"): l'AI visita il sito, legge cosa fanno davvero, capisce se hanno un problema specifico (es. mancanza di prenotazione online, sito non responsive, recensioni con lamentele sui tempi di risposta, e-commerce senza pixel/automazioni) e scrive una nota commerciale / angolo d'attacco già pronto per il venditore.

Output azionabile, non "data dump": il cliente non vuole 5.000 righe sporche; vuole 300 aziende filtrate con email/telefono/sito validati e motivo per cui contattarle oggi, esportabili in CSV o inviate via webhook a CRM / GoHighLevel / n8n / Make.

2. Stack Tecnologico Consigliato (Snello, Modulare, Margini Alti)
Per arrivare a un MVP funzionante in fretta e mantenere costi fissi bassi, usa un'architettura disaccoppiata: UI semplice + Orchestratore Workflow/Queue + Scraper/Parser + Database.

Frontend & Dashboard: Next.js (App Router) + TypeScript + Tailwind CSS (ospitato su Vercel). Ti serve per: creare campagne di ricerca, impostare filtri (settore/ATECO, area geografica, raggio/provincia, requisiti sito/contatti), vedere lo stato della pipeline e scaricare/inviare i lead.

Orchestratore / Motore di Pipeline: n8n (self-hosted su VPS) oppure Node.js / Python workers con coda (BullMQ + Redis).

Consiglio pratico: per validare e vendere i primi pacchetti/abbonamenti, n8n è velocissimo per prototipare e collegare API; quando i volumi crescono o serve controllo fine su rate-limit, retry e deduplica, sposti i nodi critici in worker Python o TypeScript.

Database & Auth: Supabase (PostgreSQL + Auth + Storage). Perfetto per gestire utenti, workspace, campagne, stati dei lead (raw -> deduped -> scraped -> enriched -> verified), log dei costi per campagna e webhook.

Scraping & Browser Automation:

HTTP leggero + parsing HTML: Cheerio (Node) o BeautifulSoup / httpx (Python) per pagine contatti, chi siamo, privacy, note legali, p.iva.

Pagine dinamiche / JS / anti-bot: Playwright (o Puppeteer) in headless su worker dedicati, abbinato a proxy residenziali (solo dove serve, per contenere i costi).

LLM / AI Enrichment: OpenAI API (gpt-4o-mini o modelli economici/veloci per estrazione e classificazione) e/o Gemini API (gemini-2.5-flash / modelli Flash per analisi contestuale veloce e strutturata con JSON Schema), usando Structured Outputs per avere campi puliti e determinati.

3. Flusso del Dato (End-to-End) e Come Ottenerlo
Il flusso deve essere a imbuto così non sprechi token AI né proxy su aziende inutili:

Seed / Discovery (Raccolta grezza):

Query geografiche + merceologiche/ATECO (es. "clinica estetica Catania", "rivendita materiali edili Palermo", "studio commercialista Ragusa").

Raccolta di: nome_attivita, indirizzo, telefono, sito_web, rating_google, numero_recensioni, place_id / id_fonte.

Normalizzazione & Deduplica (Pulizia immediata):

Normalizza nomi (rimuove S.r.l., S.n.c., punteggiatura, maiuscole), normalizza telefoni (formato +39...) e domini ([https://www.esempio.it/](https://www.esempio.it/) -> esempio.it).

Deduplica su dominio + telefono normalizzato + nome + comune/CAP (fuzzy matching). Regola d'oro: deduplica prima di fare scraping profondo e chiamate LLM.

Web Crawl Mirato (Solo se c'è un sito):

Scarica homepage + pagine ad alta densità informativa: /contatti, /chi-siamo, /about, /privacy, /cookie, /servizi, /lavora-con-noi.

Estrae testo pulito (niente menu ripetitivi o CSS/JS), link social (Facebook, Instagram, LinkedIn), email in chiaro o offuscate ([at], info at ...) e Partita IVA (pattern italiano IT + 11 cifre o 11 cifre in contesto fiscale/footer).

Enrichment & AI Scoring:

L'LLM riceve il testo estratto + metadati (categoria, recensioni, presenza social/sito) e genera un JSON strutturato: sintesi attività, dimensione stimata, segnali/opportunità, eventuale contatto/ruolo menzionato, punteggio di fit.

Verifica Contatti & Export:

Verifica sintassi/MX/deliverability delle email trovate (evitando di bruciare credito su catch-all o indirizzi morti).

Salva il record finale e lo rende disponibile in tabella, export CSV/XLSX o webhook verso CRM.

4. Come Fare Enrichment (Livelli Progressivi)
Fai l'enrichment a 3 livelli così controlli i costi e dai valore reale:

Livello 1 — Dati Strutturati & Tecnici (Basso costo, alta precisione):

Controllo dominio: esiste? Risponde HTTP 200? Ha SSL/HTTPS? È lento o su CMS/stack specifico (es. WordPress, Shopify, Wix, custom)?

Estrazione contatti pubblici sul sito: email aziendali (info@, amministrazione@,  commerciale@, eventuale email nominativa se pubblicata), telefoni, form contatti, link social.

Estrazione P.IVA dal sito (quando presente in footer/privacy).

Livello 2 — AI Context & Pain-Point Enrichment (Il vero differenziatore):

L'AI classifica l'azienda (es. B2B vs B2C, monosede vs multisede, servizio locale vs e-commerce) e identifica segnali concreti legati a ciò che vende il tuo cliente.

Esempio pratico: se il tuo cliente vende automazioni/CRM/siti/AI/marketing, l'AI può estrarre:

has_booking_or_quote_form: true/false

has_whatsapp_cta: true/false

value_proposition_summary: 1-2 frasi su cosa offrono.

outreach_hook: una frase specifica agganciata al sito o alle recensioni (non un template generico).

Livello 3 — Enrichment Societario / Contatti Chiave (Su richiesta / Secondo step):

Se hai la P.IVA (o nome + provincia), puoi interrogare fonti/API di dati aziendali italiani per ottenere forma giuridica, stato attività, codice ATECO ufficiale, area geografica/fatturato stimato o dati pubblici camerali, sempre rispettando le condizioni d'uso e la normativa privacy.

(Nota importante su GDPR e B2B: concentrati su dati di contatto aziendali pubblici—come email/telefoni pubblicati sul sito o recapiti pubblici dell'attività—evitando scraping aggressivo di dati personali privati o liste "comprate" senza chiara liceità/origine.)

5. Quali API e Servizi Ti Serviranno
Ecco la mappa pratica divisa per funzione:

Ricerca Località & Attività (Maps / Places):

Google Places API (New) oppure Serper.dev (endpoint Places/Maps) / Apify (actor Google Maps scraper): ottime per estrarre attività locali, indirizzi, telefoni, siti, rating e recensioni. Valuta i costi per chiamata/risultato prima di scalare.

Scraping / Fetching Web:

HTTP client + Playwright su tuoi container/VPS per il 70-80% dei siti normali.

Scraping API / Proxy (es. Firecrawl, Jina Reader per trasformare pagine in markdown pulito, oppure Bright Data / Oxylabs / Smartproxy per proxy residenziali) solo per siti protetti o pesanti.

LLM per Enrichment:

OpenAI API o Google Gemini API (con JSON mode / structured output e temperatura bassa, es. 0.1 - 0.2, per estrazione e classificazione affidabile).

Verifica Email (Opzionale ma consigliata prima dell'invio):

API di email validation (es. ZeroBounce, NeverBounce, MillionVerifier o controlli DNS/MX + SMTP check) per ridurre i bounce nelle campagne email.

Dati Aziendali / Registri / Enrichment Esterno (Se aggiungi il Livello 3):

Provider di dati aziendali italiani / europei (es. API camerali/societarie o provider B2B) quando ti servono codici ATECO ufficiali o dati societari strutturati.

Integrazione & Consegna:

Webhook in uscita (JSON payload verso n8n, Make, GoHighLevel, HubSpot, CRM custom) + export CSV/XLSX.

Ordine Consigliato per Costruirlo Senza Perdere Mesi
Step 1 (Giorni 1–5): Metti in piedi una pipeline su n8n (o script Python) che prende una query (settore + città/provincia), raccoglie aziende, visita il sito, estrae email/telefono/P.IVA/social e fa un prompt LLM che produce riassunto + angolo di attacco.

Step 2 (Giorni 6–10): Esporta su Google Sheets/CSV e fai 5–10 test reali su nicchie del Sud/Italia (es. studi tecnici, cliniche, rivenditori, agenzie, ho.re.ca.). Controlla a mano la percentuale di dati utili e falsi positivi.

Step 3 (Settimane 3–4): Solo quando la qualità del dato è alta, aggiungi Supabase + Next.js per gestire campagne, deduplica, crediti/costi e webhook, così puoi venderlo sia come servizio chiavi in mano sia come tool.