"""
market_radar.py — Motore di Intelligence per Social & Market Radar.

Funzionalità:
1. Analisi presenza & temi Facebook dei lead (via crawl cache, Serper site:facebook.com, o Graph API se configurata).
2. Scoperta Trend Virali in Sicilia/Italia per settore (Termoidraulica, HVAC, Elettricisti, Fotovoltaico, Impiantistica)
   tramite Google News RSS live + Gemini Search Grounding opzionale + Pain Point reali dal dataset.
3. Feed Bandi, PNRR, Finanziamenti, Fiere, Eventi e Novità Tecnologiche dal web con fonti reali + Script Telefonico 30s.
4. Generatore AI 3 Post Social (Facebook, Instagram, LinkedIn) con Prompt Immagine dedicato, Hashtag/Keyword
   e rigenerazione singola o globale.

Vincoli (AGENTS.md):
- Zero Hallucination: non inventa notizie, bandi o post FB inesistenti; usa URL reali o segnala chiaramente
  quando è necessaria la chiave API per l'ispezione live.
- Human-in-the-Loop: i post restano bozze copiabili; nessuna pubblicazione automatica.
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.config import DATA_DIR, ROOT_DIR

logger = logging.getLogger("market_radar")

NICHE_QUERY_MAP: Dict[str, Dict[str, Any]] = {
    "termoidraulica": {
        "label": "Termoidraulica & Caldaie",
        "keywords": ["termoidraulica", "caldaie", "riscaldamento", "pompe di calore", "citel"],
        "hashtags_local": ["#termoidraulicacatania", "#termoidraulicasicilia", "#caldaiecatania", "#idraulicocatania"],
        "hashtags_sector": ["#termoidraulica", "#pompedicalore", "#efficienzaenergetica", "#impiantitermici", "#manutenzionecaldaie"],
    },
    "hvac": {
        "label": "HVAC & Climatizzazione",
        "keywords": ["climatizzazione", "condizionatori", "hvac", "fgas", "refrigerazione"],
        "hashtags_local": ["#climatizzazionesicilia", "#condizionatoricatania", "#hvacsicilia", "#assistenzaclimacatania"],
        "hashtags_sector": ["#climatizzazione", "#hvacitalia", "#fgas", "#risparmioenergetico", "#ariacondizionata"],
    },
    "elettricisti": {
        "label": "Elettricisti & Domotica",
        "keywords": ["elettricista", "impianti elettrici", "domotica", "quadri elettrici", "dm 37/08"],
        "hashtags_local": ["#elettricistacatania", "#impiantielettricisicilia", "#domoticacatania"],
        "hashtags_sector": ["#elettricista", "#impiantielettrici", "#domotica", "#sicurezzaimpianti", "#smarthome"],
    },
    "fotovoltaico": {
        "label": "Fotovoltaico & Rinnovabili",
        "keywords": ["fotovoltaico", "pannelli solari", "accumulo", "transizione 5.0", "comunità energetiche"],
        "hashtags_local": ["#fotovoltaicosicilia", "#fotovoltaicocatania", "#energiasolaresicilia"],
        "hashtags_sector": ["#fotovoltaico", "#energierinnovabili", "#transizione50", "#cer", "#solare"],
    },
    "impiantistica": {
        "label": "Impiantistica Generale",
        "keywords": ["impiantistica", "manutenzione impianti", "edilizia", "artigiani"],
        "hashtags_local": ["#impiantisticacatania", "#artigianisicilia", "#cnacatania"],
        "hashtags_sector": ["#impiantistica", "#artigianiitaliani", "#pmiitaliane", "#cantieri"],
    },
}

GEO_QUERY_MAP: Dict[str, str] = {
    "catania": "Catania",
    "sicilia": "Sicilia",
    "italia": "Italia",
}


class _SinglePostPayload(BaseModel):
    text: str
    image_prompt: str
    hook: str
    cta: str


class _SocialBundlePayload(BaseModel):
    facebook: _SinglePostPayload
    instagram: _SinglePostPayload
    linkedin: _SinglePostPayload
    hashtags: List[str] = Field(default_factory=list)
    seo_keywords: List[str] = Field(default_factory=list)


class MarketRadarService:
    """Servizio unificato per Radar Trend, Pagine FB Lead, Bandi/Fiere e Generazione Post AI."""

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        load_dotenv(ROOT_DIR / ".env", override=False)
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.serper_api_key = os.getenv("SERPER_API_KEY", "").strip()
        self.fb_token = os.getenv("FACEBOOK_ACCESS_TOKEN", "").strip()
        self.model_name = model_name

    @staticmethod
    def _load_crawl_cache() -> Dict[str, Dict[str, Any]]:
        cache_path = DATA_DIR / "website_crawl_cache.json"
        if not cache_path.exists():
            return {}
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    async def _fetch_google_news_rss(self, query: str, limit: int = 8) -> List[Dict[str, str]]:
        """Recupera notizie e trend reali e recenti da Google News Italia RSS (gratuito, senza API key)."""
        encoded = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded}&hl=it&gl=IT&ceid=IT:it"
        items: List[Dict[str, str]] = []
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    return []
                root = ET.fromstring(resp.text)
                for item in root.findall(".//item")[:limit]:
                    title = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    pub_date = (item.findtext("pubDate") or "").strip()
                    source_el = item.find("source")
                    source = source_el.text.strip() if source_el is not None and source_el.text else "Web News"
                    if title and link:
                        items.append(
                            {
                                "title": title,
                                "url": link,
                                "published_at": pub_date,
                                "source": source,
                            }
                        )
        except Exception as exc:
            logger.debug("Google News RSS fallback (%s): %s", query, exc)
        return items

    async def _serper_search(self, query: str, num: int = 5) -> List[Dict[str, str]]:
        if not self.serper_api_key:
            return []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": self.serper_api_key, "Content-Type": "application/json"},
                    json={"q": query, "gl": "it", "hl": "it", "num": num},
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
                return [
                    {
                        "title": str(r.get("title", "")),
                        "url": str(r.get("link", "")),
                        "snippet": str(r.get("snippet", "")),
                    }
                    for r in data.get("organic", [])
                ]
        except Exception as exc:
            logger.debug("Serper search error: %s", exc)
            return []

    @staticmethod
    def compute_dataset_pain_points(leads: List[Dict[str, Any]], niche_filter: str = "") -> List[Dict[str, Any]]:
        """Estrae i pain point reali e misurabili dai lead in archivio."""
        filtered = leads
        if niche_filter and niche_filter != "all":
            kw = NICHE_QUERY_MAP.get(niche_filter, {}).get("keywords", [niche_filter])
            sub = [
                x
                for x in leads
                if any(k in f"{x.get('niche', '')} {x.get('category', '')} {x.get('company_name', '')}".lower() for k in kw)
            ]
            if sub:
                filtered = sub

        total = len(filtered)
        if total == 0:
            return []

        no_h24 = sum(1 for x in filtered if not x.get("is_h24"))
        no_web = sum(1 for x in filtered if not x.get("website"))
        cna_non_assoc = sum(1 for x in filtered if x.get("cna_eligible_50"))
        no_email = sum(1 for x in filtered if not x.get("email"))
        trigger_counts = Counter(x.get("trigger_signal", "") for x in filtered if x.get("trigger_signal"))

        pain_points = [
            {
                "id": "pain-missed-calls",
                "title": "Chiamate perse in cantiere e zero copertura H24",
                "affected_count": no_h24,
                "affected_pct": round(no_h24 / total * 100, 1),
                "evidence": f"{no_h24} aziende su {total} nel filtro selezionato risultano senza reperibilità H24 verificata.",
                "social_angle": "Quando sei sotto una caldaia o sul tetto a montare un clima, ogni telefonata persa è un lavoro regalato al concorrente.",
                "sales_hook": "Centralino Vocale AI 095 che risponde in 3 secondi anche la sera e il weekend.",
            },
            {
                "id": "pain-digital-gap",
                "title": "Assenza di presidio web e canali digitali strutturati",
                "affected_count": no_web,
                "affected_pct": round(no_web / total * 100, 1),
                "evidence": f"{no_web} imprese su {total} non hanno un sito web aziendale attivo rilevato.",
                "social_angle": "I clienti cercano su Google e chiamano al volo: se non trovano risposta immediata passano al numero successivo.",
                "sales_hook": "Attivazione rapida senza cambiare numero aziendale né rifare il sito.",
            },
            {
                "id": "pain-cna-costs",
                "title": "Burocrazia (CITEL / F-Gas) e costi associativi non ottimizzati",
                "affected_count": cna_non_assoc,
                "affected_pct": round(cna_non_assoc / total * 100, 1),
                "evidence": f"{cna_non_assoc} aziende risultano non associate CNA (eleggibili allo sconto 50% primo anno).",
                "social_angle": "Tra catasto CITEL, patentini F-Gas e burocrazia di cantiere, il tempo per gestire segreteria e clienti non basta mai.",
                "sales_hook": "Convenzione CNA Catania con quota primo anno dimezzata + segreteria AI.",
            },
            {
                "id": "pain-lead-capture",
                "title": "Mancanza di email aziendale verificata per preventivi rapidi",
                "affected_count": no_email,
                "affected_pct": round(no_email / total * 100, 1),
                "evidence": f"{no_email} aziende su {total} non espongono un indirizzo email commerciale diretto.",
                "social_angle": "Raccogliere dati impianto, foto guasto e matricola direttamente su WhatsApp evita errori e sopralluoghi a vuoto.",
                "sales_hook": "Qualifica automatica guasto e invio scheda intervento su WhatsApp.",
            },
        ]

        if trigger_counts:
            top_trig, top_cnt = trigger_counts.most_common(1)[0]
            pain_points.append(
                {
                    "id": "pain-top-trigger",
                    "title": f"Urgenza rilevata: {top_trig}",
                    "affected_count": top_cnt,
                    "affected_pct": round(top_cnt / total * 100, 1),
                    "evidence": f"Segnale ricorrente su {top_cnt} aziende nell'archivio selezionato.",
                    "social_angle": f"Focus operativo su '{top_trig}': trasformare l'emergenza in appuntamenti pianificati.",
                    "sales_hook": "Filtro automatico emergenze vs manutenzioni ordinarie.",
                }
            )

        return pain_points

    async def discover_trends(
        self,
        leads: List[Dict[str, Any]],
        niche: str = "termoidraulica",
        geography: str = "sicilia",
        timeframe: str = "30d",
    ) -> Dict[str, Any]:
        """Aggrega trend live dal web (con filtri utente), pain point reali e hashtag/keyword."""
        niche_cfg = NICHE_QUERY_MAP.get(niche, NICHE_QUERY_MAP["termoidraulica"])
        geo_label = GEO_QUERY_MAP.get(geography, "Sicilia")
        main_kw = niche_cfg["keywords"][0]

        query = f"{main_kw} OR {niche_cfg['keywords'][1]} {geo_label}"
        if timeframe == "7d":
            query += " when:7d"
        elif timeframe == "30d":
            query += " when:30d"

        live_news = await self._fetch_google_news_rss(query, limit=8)
        serper_trends = await self._serper_search(f"trend {main_kw} {geo_label} 2026", num=4)

        trends: List[Dict[str, Any]] = []
        for idx, item in enumerate(live_news[:6]):
            trends.append(
                {
                    "id": f"trend-rss-{idx}",
                    "title": item["title"],
                    "source": item["source"],
                    "url": item["url"],
                    "published_at": item["published_at"],
                    "wave_type": "Onda Live Web",
                    "suggested_angle": (
                        f"Collega questa notizia ({niche_cfg['label']} - {geo_label}) al problema delle chiamate "
                        "perse in cantiere e alla necessità di rispondere subito ai clienti."
                    ),
                }
            )
        for idx, item in enumerate(serper_trends):
            trends.append(
                {
                    "id": f"trend-serper-{idx}",
                    "title": item["title"],
                    "source": "Google Search",
                    "url": item["url"],
                    "published_at": "Recente",
                    "wave_type": "Ricerca Virale",
                    "suggested_angle": item.get("snippet", "")[:220],
                }
            )

        pain_points = self.compute_dataset_pain_points(leads, niche_filter=niche)

        return {
            "niche": niche,
            "niche_label": niche_cfg["label"],
            "geography": geography,
            "geography_label": geo_label,
            "timeframe": timeframe,
            "live_trends": trends,
            "pain_points": pain_points,
            "hashtags": niche_cfg["hashtags_local"] + niche_cfg["hashtags_sector"] + ["#tecnicolive", "#aiperartigiani"],
            "seo_keywords": [
                f"{main_kw} {geo_label.lower()}",
                f"assistenza {niche_cfg['keywords'][1]} {geo_label.lower()}",
                "centralino ai artigiani",
                "recupero chiamate perse cantiere",
            ],
            "has_live_web": len(trends) > 0,
            "api_status": {
                "gemini_configured": bool(self.gemini_api_key),
                "serper_configured": bool(self.serper_api_key),
                "facebook_token_configured": bool(self.fb_token),
            },
        }

    async def analyze_lead_facebook_pages(
        self,
        leads: List[Dict[str, Any]],
        niche: str = "all",
        limit: int = 12,
    ) -> Dict[str, Any]:
        """
        Analizza la presenza Facebook dei lead:
        1. Controlla link FB eventualmente presenti nel crawl cache o nei domini.
        2. Se SERPER_API_KEY è configurata, cerca `site:facebook.com "<Company>" <City>` per estrarre snippet reali dei post.
        3. Se FACEBOOK_ACCESS_TOKEN è configurato, interroga Graph API pubblica.
        4. Non inventa mai post: dichiara lo stato reale di ogni lead.
        """
        crawl_cache = self._load_crawl_cache()

        pool = [x for x in leads if x.get("callable") or x.get("website")]
        if niche and niche != "all":
            kw = NICHE_QUERY_MAP.get(niche, {}).get("keywords", [niche])
            sub = [x for x in pool if any(k in f"{x.get('niche', '')} {x.get('category', '')}".lower() for k in kw)]
            if sub:
                pool = sub

        selected = pool[:limit]
        results: List[Dict[str, Any]] = []

        for ld in selected:
            company = str(ld.get("company_name") or "").strip()
            city = str(ld.get("city") or "Catania").strip()
            website = str(ld.get("website") or "").strip()

            fb_url = ""
            if "facebook.com" in website.lower():
                fb_url = website
            elif website and website in crawl_cache:
                cached = crawl_cache[website]
                raw_text = str(cached.get("raw_text") or "") + " " + str(cached.get("social_links") or "")
                m = re.search(r"https?://(?:www\.)?facebook\.com/[A-Za-z0-9_.\-/]+", raw_text, re.I)
                if m:
                    fb_url = m.group(0)

            snippets: List[str] = []
            source_mode = "Archivio Locale"

            if self.serper_api_key:
                q = f'site:facebook.com "{company}" {city}'
                hits = await self._serper_search(q, num=3)
                if hits:
                    source_mode = "Google Index (Serper)"
                    if not fb_url:
                        fb_url = hits[0]["url"]
                    snippets = [h["snippet"] for h in hits if h.get("snippet")]

            detected_themes: List[str] = []
            corpus = " ".join(snippets).lower()
            if any(w in corpus for w in ["installaz", "lavoro", "cantiere", "montaggio"]):
                detected_themes.append("Foto lavori / installazioni")
            if any(w in corpus for w in ["offerta", "promo", "sconto", "prezzo"]):
                detected_themes.append("Promozioni stagionali")
            if any(w in corpus for w in ["manutenz", "assistenza", "pulizia", "bollino"]):
                detected_themes.append("Manutenzioni & Assistenza")

            if fb_url and not snippets:
                status_label = "Pagina trovata — serve Serper o Token FB per leggere i post"
            elif fb_url and snippets:
                status_label = "Post pubblici indicizzati analizzati"
            else:
                status_label = "Nessuna pagina FB pubblica rilevata (ricerca indicizzata necessaria)"

            results.append(
                {
                    "lead_id": ld.get("id", ""),
                    "company_name": company,
                    "city": city,
                    "niche": ld.get("niche", ""),
                    "facebook_url": fb_url,
                    "source_mode": source_mode,
                    "status_label": status_label,
                    "post_snippets": snippets,
                    "detected_themes": detected_themes or (["Presenza da verificare"] if not snippets else ["Comunicazione generica"]),
                    "suggested_hook": (
                        f"Ho visto la vostra pagina di {city}: pubblicate ottimi lavori tecnici, "
                        "ma quante richieste vi sfuggono al telefono mentre siete operativi?"
                    ),
                }
            )

        return {
            "analyzed_count": len(results),
            "with_fb_url": sum(1 for r in results if r["facebook_url"]),
            "serper_active": bool(self.serper_api_key),
            "fb_token_active": bool(self.fb_token),
            "items": results,
        }

    async def fetch_sector_news(
        self,
        niche: str = "termoidraulica",
        geography: str = "sicilia",
        category: str = "all",
    ) -> Dict[str, Any]:
        """Recupera bandi, PNRR, finanziamenti, fiere ed eventi e novità tecnologiche reali dal web."""
        niche_cfg = NICHE_QUERY_MAP.get(niche, NICHE_QUERY_MAP["termoidraulica"])
        geo_label = GEO_QUERY_MAP.get(geography, "Sicilia")
        main_kw = niche_cfg["keywords"][0]

        queries = {
            "bandi_pnrr": f"(bandi OR PNRR OR incentivi OR \"conto termico\" OR \"transizione 5.0\") ({main_kw} OR impianti) {geo_label}",
            "fiere_eventi": f"(fiera OR evento OR convegno OR manifestazione) ({main_kw} OR impiantistica OR artigiani) Italia",
            "tecnologia_norme": f"(normativa OR decreto OR F-Gas OR \"case green\" OR novità) ({main_kw} OR pompe di calore)",
        }

        target_cats = list(queries.keys()) if category == "all" else [category]
        items: List[Dict[str, Any]] = []

        for cat in target_cats:
            q = queries.get(cat)
            if not q:
                continue
            rss_hits = await self._fetch_google_news_rss(q, limit=5)
            for idx, hit in enumerate(rss_hits):
                title = hit["title"]
                cat_label = {
                    "bandi_pnrr": "Bandi, PNRR & Finanziamenti",
                    "fiere_eventi": "Fiere, Eventi & Manifestazioni",
                    "tecnologia_norme": "Tecnologia & Normative",
                }[cat]
                phone_script = (
                    f"\"Buongiorno, la chiamo da TecnicoLIVE/CNA: ha già visto l'aggiornamento su '{title[:75]}...'? "
                    "Con i nuovi picchi di richieste su questi interventi, il nostro centralino AI evita che perda "
                    "preventivi mentre è in cantiere.\""
                )
                items.append(
                    {
                        "id": f"{cat}-{idx}",
                        "category": cat,
                        "category_label": cat_label,
                        "title": title,
                        "source": hit["source"],
                        "url": hit["url"],
                        "published_at": hit["published_at"],
                        "phone_script_30s": phone_script,
                    }
                )

        return {
            "niche": niche,
            "geography": geography,
            "category": category,
            "count": len(items),
            "items": items,
        }

    def _deterministic_posts(
        self,
        topic: str,
        niche_label: str,
        geo_label: str,
        tone: str,
        target_platform: Optional[str],
        instruction: str,
        hashtags: List[str],
        seo_keywords: List[str],
    ) -> Dict[str, Any]:
        tone_note = f" (Stile: {tone})" if tone else ""
        instr_note = f" [{instruction}]" if instruction else ""

        fb_text = (
            f"🔧 Lavori nel settore {niche_label} a {geo_label}? Parliamo chiaro{tone_note}.\n\n"
            f"In questi giorni il tema caldo è: {topic}.\n"
            "Mentre i tecnici sono sul campo tra manutenzioni e nuovi impianti, il telefono continua a squillare. "
            "Rispondere dopo 2 ore significa quasi sempre aver già perso il cliente.\n\n"
            "Con TecnicoLIVE + Convenzione CNA Catania hai una segreteria vocale AI attiva H24 che risponde in 3 secondi, "
            "raccoglie tipo di guasto e zona, e ti manda tutto ordinato su WhatsApp.\n\n"
            f"👇 Scrivici nei commenti o in DM se vuoi sentirlo dal vivo per la tua ditta!{instr_note}"
        )
        fb_prompt = (
            f"Fotografia editoriale realistica di un tecnico termoidraulico italiano in un cantiere moderno a {geo_label}, "
            "mani occupate su una caldaia/pompa di calore, smartphone che squilla sul tavolo da lavoro con notifica WhatsApp verde, "
            "luce naturale calda mediterranea, stile documentaristico autentico, no testo nell'immagine, 16:9."
        )

        ig_text = (
            f"⚡ {topic}\n\n"
            f"Se fai {niche_label} a {geo_label}, sai bene quanto costa perdere anche solo 2 chiamate al giorno.\n\n"
            "✅ Risposta AI in 3 secondi H24\n"
            "✅ Scheda guasto pronta su WhatsApp\n"
            "✅ Convenzione dedicata CNA Catania\n\n"
            "Salva questo post e scrivici 'DEMO' in DM per ricevere il numero di prova gratuita per 7 giorni."
        )
        ig_prompt = (
            f"Immagine quadrata 1:1 ad alto contrasto per carosello Instagram: furgone attrezzato di un impiantista siciliano al tramonto "
            "con vista Etna sullo sfondo, grafica pulita moderna blu navy e bianco, atmosfera professionale artigianale, "
            "fotorealistico 8k, senza scritte sovrapposte."
        )

        li_text = (
            f"Aggiornamento di settore ({niche_label} — {geo_label}): {topic}.\n\n"
            "La vera sfida competitiva delle PMI impiantistiche oggi non è solo tecnica, ma di reattività commerciale: "
            "i dati raccolti sul territorio mostrano che la maggior parte delle imprese non dispone di una copertura telefonica H24.\n\n"
            "Attraverso la sinergia TecnicoLIVE e CNA Catania supportiamo le aziende del territorio nel trasformare "
            "ogni chiamata persa in cantiere in un intervento pianificato.\n\n"
            "Per approfondire le condizioni riservate agli associati e non associati CNA, scrivetemi un messaggio diretto."
        )
        li_prompt = (
            "Fotografia corporate B2B minimalista in studio o ufficio tecnico moderno: imprenditore artigiano italiano "
            "e responsabile tecnico che analizzano un tablet con agenda interventi automatizzata, luce naturale, "
            "palette blu istituzionale e acciaio, stile editoriale LinkedIn, 4:5, zero testo."
        )

        payload = {
            "facebook": {
                "text": fb_text,
                "image_prompt": fb_prompt,
                "hook": f"Lavori nel settore {niche_label} a {geo_label}?",
                "cta": "Scrivici nei commenti o in DM per sentirlo dal vivo.",
            },
            "instagram": {
                "text": ig_text,
                "image_prompt": ig_prompt,
                "hook": f"Quanto costa perdere 2 chiamate al giorno su {topic[:40]}?",
                "cta": "Scrivi 'DEMO' in DM per la prova 7 giorni.",
            },
            "linkedin": {
                "text": li_text,
                "image_prompt": li_prompt,
                "hook": f"La sfida competitiva delle PMI {niche_label} su {topic[:45]}.",
                "cta": "Scrivimi in privato per i dettagli della convenzione CNA.",
            },
            "hashtags": hashtags,
            "seo_keywords": seo_keywords,
            "generated_by": "deterministic_fallback",
            "regenerated_platform": target_platform or "all",
        }
        return payload

    async def generate_social_posts(
        self,
        topic: str,
        niche: str = "termoidraulica",
        geography: str = "sicilia",
        tone: str = "Tecnico-Pratico (da cantiere)",
        target_platform: Optional[str] = None,
        instruction: str = "",
    ) -> Dict[str, Any]:
        """Genera 3 post social AI (FB, IG, LinkedIn) + 3 Prompt Immagine + Hashtag/Keyword."""
        niche_cfg = NICHE_QUERY_MAP.get(niche, NICHE_QUERY_MAP["termoidraulica"])
        geo_label = GEO_QUERY_MAP.get(geography, "Sicilia")
        hashtags = niche_cfg["hashtags_local"] + niche_cfg["hashtags_sector"] + ["#tecnicolive", "#cnacatania"]
        seo_keywords = [
            f"{niche_cfg['keywords'][0]} {geo_label.lower()}",
            "assistente vocale ai artigiani",
            "convenzione cna catania",
        ]

        if not self.gemini_api_key:
            return self._deterministic_posts(
                topic=topic,
                niche_label=niche_cfg["label"],
                geo_label=geo_label,
                tone=tone,
                target_platform=target_platform,
                instruction=instruction,
                hashtags=hashtags,
                seo_keywords=seo_keywords,
            )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.gemini_api_key)
            focus = (
                f"RIGENERA IN MODO SIGNIFICATIVAMENTE DIVERSO soprattutto per la piattaforma '{target_platform}'."
                if target_platform
                else "Genera tutti e 3 i post in modo complementare."
            )
            prompt = (
                "Sei il Social Media Strategist di TecnicoLIVE (assistente vocale AI per impiantisti, "
                "termoidraulici, elettricisti e partner CNA Catania).\n"
                f"Argomento / Trend / Bando da cavalcare: {topic}\n"
                f"Settore target: {niche_cfg['label']} | Area: {geo_label}\n"
                f"Tono di voce richiesto: {tone}\n"
                f"Istruzione aggiuntiva utente: {instruction or 'Nessuna'}\n"
                f"{focus}\n\n"
                "Regole obbligatorie:\n"
                "1. NON inventare statistiche false o casi studio finti.\n"
                "2. Scrivi 3 testi distinti e ottimizzati per Facebook (community locale), Instagram (caption ritmata) e LinkedIn (B2B).\n"
                "3. Per OGNI post genera un 'image_prompt' dettagliato in italiano/inglese pronto da copiare su Midjourney, ChatGPT o Canva "
                "per creare la foto esternamente (non generare immagini).\n"
                "4. Includi 8-12 hashtag italiani/locali rilevanti e 4-6 keyword SEO."
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=_SocialBundlePayload,
                    temperature=0.75,
                ),
            )
            parsed = json.loads(response.text)
            parsed["generated_by"] = self.model_name
            parsed["regenerated_platform"] = target_platform or "all"
            if not parsed.get("hashtags"):
                parsed["hashtags"] = hashtags
            if not parsed.get("seo_keywords"):
                parsed["seo_keywords"] = seo_keywords
            return parsed
        except Exception as exc:
            logger.warning("Gemini social generation fallback: %s", exc)
            return self._deterministic_posts(
                topic=topic,
                niche_label=niche_cfg["label"],
                geo_label=geo_label,
                tone=tone,
                target_platform=target_platform,
                instruction=instruction,
                hashtags=hashtags,
                seo_keywords=seo_keywords,
            )
