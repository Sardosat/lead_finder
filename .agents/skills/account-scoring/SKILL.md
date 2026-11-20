---
name: account-scoring
description: "Algoritmo di qualificazione predittiva ICP Fit (0-100) e suddivisione automatica in Tier A (VIP/Hot), Tier B (Warm) e Tier C (Cold) per prioritizzare le chiamate e le campagne Meta Ads."
metadata:
  author: TecnicoLIVE & Clay Intelligence
  version: 1.0.0
---

# Account Scoring & Lead Tiering (0-100) — TecnicoLIVE

La skill **account-scoring** permette di valutare all'istante il potenziale economico di ciascuna ditta impiantistica censita, evitando che i collaboratori sprechino ore al telefono su contatti a basso rendimento.

## Tabella Punteggi ICP Fit (Totale: 100 Punti)

| Criterio di Valutazione | Punteggio Assegnato | Giustificazione Commerciale |
|---|---|---|
| **Cellulare Diretto / Reperibile (Prefisso `3xx`)** | **+25 pt** | Permette il contatto immediato su WhatsApp e la ricezione delle notifiche dell'assistente vocale. |
| **Partita IVA Attiva con Luhn Checksum** | **+20 pt** | Ditta regolarmente registrata e solvibile (zero hobbisti o abusivi). |
| **Marchi Assistiti Compatibili (Vaillant, Buderus, Baxi, Bosch)** | **+20 pt** | La ditta può sfruttare immediatamente la libreria manuali tecnici di TecnicoLIVE. |
| **Sito Web Attivo / Digital Footprint** | **+20 pt** | Azienda strutturata che investe nella propria visibilità e riceve traffico. |
| **Stato Non Associato CNA Catania** | **+15 pt** | Massima leva di vendita: pacchetto combinato con quota 1° anno scontata. |

## Suddivisione nei 3 Tier Operativi

- 🔥 **Tier A (Score 80 - 100)**: **Massima Priorità**. Assegnato ai collaboratori per chiamata telefonica diretta entro 24 ore e invio demo WhatsApp.
- 🟡 **Tier B (Score 55 - 79)**: **Priorità Media**. Inserito nelle Smart Lists di RSK System per campagne Meta Ads Retargeting (Scenario 1 e 3).
- ❄️ **Tier C (Score < 55)**: **Bassa Priorità / Nurturing**. Contatti incompleti o privi di sito web, destinati a sequenze di recupero.
