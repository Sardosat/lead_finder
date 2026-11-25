4. Piano d'Azione Operativo in 4 Milestone
Milestone 1 (Settimana 1) — Generalizzazione del Motore Python Esistente (Multi-Nicchia & Multi-Comune ISTAT)

Prima di costruire il frontend SaaS, trasformiamo il codice attuale di lead_finder da "hardcoded su Catania + impiantisti" a motore generico configurabile via Campaign Spec:

[NEW] src/campaign_schema.py: modelli Pydantic per CampaignConfig (settore/ATECO, lista comuni/province ISTAT, offerta del cliente, anti-personas custom, livelli enrichment abilitati) e LeadRecord (schema canonico IT/EU).

[NEW] src/connectors/places_connector.py: connettore seed verso Google Places API (New) e/o Serper.dev Places (risolve subito il problema dei telefoni mancanti e porta la copertura a qualsiasi città/settore italiano ed europeo!).

[NEW] src/connectors/vies_validator.py: validazione ufficiale gratuita VIES Commissione Europea su Partita IVA IT/EU (verifica in tempo reale che la P.IVA sia attiva e restituisce ragione sociale/indirizzo ufficiali!).

[NEW] src/enrichment/tech_audit.py: estensione di website_crawler.py per Livello 1 completo (http_status, has_ssl, cms_stack, has_meta_pixel, has_whatsapp_cta, has_booking_form, social_links, estrazione email offuscate [at] + verifica DNS/MX in Python con dnspython).

[NEW] src/enrichment/llm_qualifier.py: Livello 2 reale con Structured Outputs JSON (Gemini Flash / OpenAI gpt-4o-mini, temperature=0.1) che legge il sito + recensioni Google e genera ai_summary, detected_pain_points, icp_fit_score, outreach_hook — con strict Zero Hallucination (ogni affermazione deve citare una prova testuale presente nella pagina!).

[NEW] src/exporters/webhook_exporter.py: payload JSON standardizzato per invio (sempre previa conferma umana) a RSK System / GoHighLevel / n8n / Make + CSV/XLSX.


Milestone 2 (Settimana 2) — Validazione su 5 Nicchie Italiane + Arricchimento Camerale (Livello 3)

[NEW] src/connectors/italian_registry.py: adapter pluggable per API camerali italiane (es. OpenAPI.it IT-advanced / IT-start per Codice ATECO, forma giuridica, PEC, stato attività, fascia fatturato/bilancio) con budget cap e caching locale per P.IVA.

Test reali sul campo: eseguire la pipeline su 5 nicchie PMI reali (es. Impiantisti/Fotovoltaico Catania, Cliniche Estetiche/Dentistiche Palermo, Rivendite Edili Sicilia, Studi Tecnici/Architetti, Agenzie Immobiliari) e misurare 4 KPI oggettivi: % telefoni E.164, % email MX valide, % P.IVA/VIES attive, % zero falsi positivi geografici (confronto diretto contro esempio.csv come case study di vendita!).

Milestone 3 (Settimane 3–4) — Backend Multi-Tenant (Supabase + FastAPI Worker) & Web App SaaS (Next.js)
Database Supabase (PostgreSQL in regione EU Francoforte/Milano): schema multi-tenant con Row Level Security (workspaces, campaigns, leads, enrichment_jobs, credits_ledger, suppression_list globale per opt-out GDPR).

API & Worker (FastAPI + coda asincrona): orchestrazione job per campagna con avanzamento live (raw → deduped → l1_crawled → l2_ai_qualified → l3_registry → ready), rate-limit e contabilizzazione crediti/costi per riga.

Frontend Next.js + TypeScript + Tailwind:
Wizard 3-step "Crea Campagna" (Settore/ATECO + Area ISTAT + Cosa vendi tu → prompt AI auto-calibrato!).
Tabella operativa stile Clay semplificata (filtri Tier A/B/C, stato P.IVA/VIES, pain points evidenziati, anteprima icebreaker).

Pulsanti Esporta CSV/Excel e Invia a RSK System / Webhook (con gate di revisione umano + blacklist GDPR).

Bridge di Upsell Integrato: "Hai 280 lead qualificati pronti — Attiva il tuo centralino AI / CRM RSK System & TecnicoLIVE per gestirli e convertirli".

Milestone 4 (Settimane 5–8) — Billing, Playbook Verticali & Go-To-Market
Stripe Billing + Pacchetti Crediti (es. Piani SaaS ricorrenti + pacchetti "Chiavi in mano / Done-For-You" per i primi 10 clienti paganti).

Template Verticali Pronti (Impiantistica & Energia, Agenzie Web/Marketing, Edilizia & Appalti, Ho.Re.Ca., Sanità/Cliniche) + Landing page con il confronto reale "Clay.com vs Noi su Catania" (usando proprio il caso Ecuador/Valverde!).