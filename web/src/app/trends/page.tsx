"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertCircle,
  ArrowUpRight,
  Check,
  ChevronDown,
  Copy,
  ExternalLink,
  Flame,
  Hash,
  Image as ImageIcon,
  Newspaper,
  PhoneCall,
  RefreshCw,
  Share2,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { SeasonalityTrendChart } from "@/components/charts/SeasonalityTrendChart";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/formatters";
import type { SavedSearch, TrendsResponse } from "@/lib/types";

type RadarTab = "trends_pains" | "fb_leads" | "sector_news" | "social_ai" | "lead_demand";
type PlatformKey = "facebook" | "instagram" | "linkedin";

interface LiveTrendItem {
  id: string;
  title: string;
  source: string;
  url: string;
  published_at: string;
  wave_type: string;
  suggested_angle: string;
}

interface PainPointItem {
  id: string;
  title: string;
  affected_count: number;
  affected_pct: number;
  evidence: string;
  social_angle: string;
  sales_hook: string;
}

interface RadarTrendsPayload {
  niche: string;
  niche_label: string;
  geography_label: string;
  live_trends: LiveTrendItem[];
  pain_points: PainPointItem[];
  hashtags: string[];
  seo_keywords: string[];
  api_status: {
    gemini_configured: boolean;
    serper_configured: boolean;
    facebook_token_configured: boolean;
  };
}

interface FbLeadItem {
  lead_id: string;
  company_name: string;
  city: string;
  niche: string;
  facebook_url: string;
  source_mode: string;
  status_label: string;
  post_snippets: string[];
  detected_themes: string[];
  suggested_hook: string;
}

interface SectorNewsItem {
  id: string;
  category: string;
  category_label: string;
  title: string;
  source: string;
  url: string;
  published_at: string;
  phone_script_30s: string;
}

interface SocialPostCard {
  text: string;
  image_prompt: string;
  hook: string;
  cta: string;
}

interface SocialBundlePayload {
  facebook: SocialPostCard;
  instagram: SocialPostCard;
  linkedin: SocialPostCard;
  hashtags: string[];
  seo_keywords: string[];
  generated_by: string;
}

async function postBackend<T>(path: string, body: Record<string, unknown>): Promise<T> {
  const res = await fetch(`/api/backend${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`Errore API ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export default function SocialMarketRadarPage() {
  const [activeTab, setActiveTab] = useState<RadarTab>("trends_pains");

  const [searchId, setSearchId] = useState("ds-master-clean");
  const [niche, setNiche] = useState("termoidraulica");
  const [geography, setGeography] = useState("sicilia");
  const [timeframe, setTimeframe] = useState("30d");

  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [legacyData, setLegacyData] = useState<TrendsResponse | null>(null);
  const [openDriver, setOpenDriver] = useState<string>("cna-50");

  const [trendsData, setTrendsData] = useState<RadarTrendsPayload | null>(null);
  const [trendsLoading, setTrendsLoading] = useState(false);

  const [fbItems, setFbItems] = useState<FbLeadItem[]>([]);
  const [fbMeta, setFbMeta] = useState<{ with_fb_url: number; serper_active: boolean; fb_token_active: boolean } | null>(null);
  const [fbLoading, setFbLoading] = useState(false);

  const [newsCategory, setNewsCategory] = useState("all");
  const [newsItems, setNewsItems] = useState<SectorNewsItem[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);

  const [socialTopic, setSocialTopic] = useState("Picco interventi e chiamate perse in cantiere: come rispondere H24");
  const [socialTone, setSocialTone] = useState("Tecnico-Pratico (da cantiere)");
  const [socialInstruction, setSocialInstruction] = useState("");
  const [socialBundle, setSocialBundle] = useState<SocialBundlePayload | null>(null);
  const [socialBusy, setSocialBusy] = useState<PlatformKey | "all" | null>(null);

  const [copiedKey, setCopiedKey] = useState("");

  const copyText = async (key: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(""), 1600);
    } catch {
      // ignore clipboard errors
    }
  };

  useEffect(() => {
    api
      .getSearches()
      .then((res) => setSearches(res.searches.filter((s) => s.leads_count > 0)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    api.getTrends(searchId).then(setLegacyData).catch(() => {});
  }, [searchId]);

  const loadTrends = useCallback(async () => {
    setTrendsLoading(true);
    try {
      const res = await postBackend<RadarTrendsPayload>("/radar/trends", {
        search_id: searchId,
        niche,
        geography,
        timeframe,
      });
      setTrendsData(res);
    } catch {
      // ignore
    } finally {
      setTrendsLoading(false);
    }
  }, [searchId, niche, geography, timeframe]);

  const loadFbLeads = useCallback(async () => {
    setFbLoading(true);
    try {
      const res = await postBackend<{
        items: FbLeadItem[];
        with_fb_url: number;
        serper_active: boolean;
        fb_token_active: boolean;
      }>("/radar/facebook-leads", {
        search_id: searchId,
        niche,
        limit: 15,
      });
      setFbItems(res.items || []);
      setFbMeta({
        with_fb_url: res.with_fb_url,
        serper_active: res.serper_active,
        fb_token_active: res.fb_token_active,
      });
    } catch {
      // ignore
    } finally {
      setFbLoading(false);
    }
  }, [searchId, niche]);

  const loadSectorNews = useCallback(async () => {
    setNewsLoading(true);
    try {
      const res = await postBackend<{ items: SectorNewsItem[] }>("/radar/sector-news", {
        niche,
        geography,
        category: newsCategory,
      });
      setNewsItems(res.items || []);
    } catch {
      // ignore
    } finally {
      setNewsLoading(false);
    }
  }, [niche, geography, newsCategory]);

  useEffect(() => {
    loadTrends();
  }, [loadTrends]);

  useEffect(() => {
    if (activeTab === "fb_leads" && fbItems.length === 0) {
      loadFbLeads();
    } else if (activeTab === "sector_news") {
      loadSectorNews();
    }
  }, [activeTab, fbItems.length, loadFbLeads, loadSectorNews]);

  const generatePosts = async (platform?: PlatformKey, customTopic?: string) => {
    const topicToUse = (customTopic ?? socialTopic).trim();
    if (!topicToUse) return;
    setSocialBusy(platform ?? "all");
    try {
      const res = await postBackend<SocialBundlePayload>("/radar/social-posts", {
        topic: topicToUse,
        niche,
        geography,
        tone: socialTone,
        target_platform: platform ?? null,
        instruction: socialInstruction,
      });
      if (platform && socialBundle) {
        setSocialBundle({
          ...socialBundle,
          [platform]: res[platform],
          hashtags: res.hashtags,
          seo_keywords: res.seo_keywords,
          generated_by: res.generated_by,
        });
      } else {
        setSocialBundle(res);
      }
    } catch {
      // ignore
    } finally {
      setSocialBusy(null);
    }
  };

  const sendTopicToSocialAI = (topic: string) => {
    setSocialTopic(topic);
    setActiveTab("social_ai");
    generatePosts(undefined, topic);
  };

  const signals = legacyData?.real_intent_signals;

  return (
    <div className="space-y-5 max-w-[1440px]">
      <div className="surface-panel p-3.5 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
              Settore / Nicchia
            </label>
            <select
              value={niche}
              onChange={(e) => setNiche(e.target.value)}
              className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px] font-medium"
            >
              <option value="termoidraulica">Termoidraulica &amp; Caldaie</option>
              <option value="hvac">HVAC &amp; Climatizzazione</option>
              <option value="elettricisti">Elettricisti &amp; Domotica</option>
              <option value="fotovoltaico">Fotovoltaico &amp; Rinnovabili</option>
              <option value="impiantistica">Impiantistica Generale</option>
            </select>
          </div>

          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
              Area Geografica
            </label>
            <select
              value={geography}
              onChange={(e) => setGeography(e.target.value)}
              className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px] font-medium"
            >
              <option value="catania">Catania &amp; Provincia</option>
              <option value="sicilia">Sicilia</option>
              <option value="italia">Italia</option>
            </select>
          </div>

          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
              Orizzonte Trend
            </label>
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px] font-medium"
            >
              <option value="7d">Ultimi 7 giorni</option>
              <option value="30d">Ultimo mese</option>
              <option value="season">Stagione corrente</option>
            </select>
          </div>

          <div className="flex flex-col gap-0.5">
            <label className="text-[10px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
              Archivio Lead
            </label>
            <select
              value={searchId}
              onChange={(e) => setSearchId(e.target.value)}
              className="h-8 max-w-[240px] rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px] font-medium"
            >
              {searches.length === 0 ? (
                <option value="ds-master-clean">Archivio Master Aziende Pulite</option>
              ) : (
                searches.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({formatNumber(s.leads_count)})
                  </option>
                ))
              )}
            </select>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              loadTrends();
              if (activeTab === "fb_leads") loadFbLeads();
              if (activeTab === "sector_news") loadSectorNews();
            }}
            className="flex h-8 items-center gap-1.5 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[12px] font-medium hover:bg-[var(--bg-subtle)]"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${trendsLoading ? "animate-spin" : ""}`} />
            <span>Aggiorna Radar</span>
          </button>
          <Link
            href={`/leads?search_id=${encodeURIComponent(searchId)}`}
            className="flex h-8 items-center gap-1 rounded bg-[#1D4ED8] px-3 text-[12px] font-medium text-white hover:bg-blue-800"
          >
            <span>Apri Lead Finder</span>
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap gap-5 border-b border-[var(--border-hairline)] text-[13px]">
        {[
          { id: "trends_pains", label: "Trend Virali, Pain Point & Hashtag", icon: Flame },
          { id: "fb_leads", label: "Analisi Pagine FB dei Lead", icon: Share2 },
          { id: "sector_news", label: "Bandi, PNRR, Fiere & Novità", icon: Newspaper },
          { id: "social_ai", label: "3 Post Social AI (FB / IG / LinkedIn)", icon: Sparkles },
          { id: "lead_demand", label: "Analisi Domanda & Segnali Lead", icon: TrendingUp },
        ].map((t) => {
          const Icon = t.icon;
          const active = activeTab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setActiveTab(t.id as RadarTab)}
              className={`flex items-center gap-1.5 pb-2.5 font-medium border-b-2 transition-colors ${
                active
                  ? "border-[#1D4ED8] text-[#1D4ED8]"
                  : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {activeTab === "trends_pains" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="surface-panel overflow-hidden">
              <div className="border-b border-[var(--border-hairline)] px-4 py-3 flex items-center justify-between">
                <div>
                  <h2 className="text-[13px] font-semibold">
                    Onde Virali &amp; Trend ({trendsData?.niche_label || niche} — {trendsData?.geography_label || geography})
                  </h2>
                  <p className="text-[12px] text-[var(--text-muted)]">
                    Notizie reali dal web pronte da cavalcare nei tuoi post social
                  </p>
                </div>
              </div>
              <div className="divide-y divide-[var(--border-hairline)]">
                {trendsLoading && (
                  <div className="p-4 text-[12px] text-[var(--text-muted)]">Ricerca trend live in corso...</div>
                )}
                {!trendsLoading && (!trendsData || trendsData.live_trends.length === 0) && (
                  <div className="p-4 text-[12px] text-[var(--text-muted)]">
                    Nessun trend live recuperato al momento. Verifica la connessione o cambia filtri.
                  </div>
                )}
                {trendsData?.live_trends.map((tr) => (
                  <div key={tr.id} className="p-3.5 space-y-1.5 hover:bg-[var(--bg-subtle)]">
                    <div className="flex items-start justify-between gap-2">
                      <a
                        href={tr.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[13px] font-medium text-[#1D4ED8] hover:underline flex items-center gap-1"
                      >
                        <span>{tr.title}</span>
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                      <span className="shrink-0 rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-[#1D4ED8]">
                        {tr.source}
                      </span>
                    </div>
                    <p className="text-[12px] text-[var(--text-secondary)]">{tr.suggested_angle}</p>
                    <div className="pt-1">
                      <button
                        type="button"
                        onClick={() => sendTopicToSocialAI(tr.title)}
                        className="inline-flex items-center gap-1 rounded border border-[#1D4ED8] px-2.5 py-1 text-[11px] font-medium text-[#1D4ED8] hover:bg-blue-50"
                      >
                        <Sparkles className="h-3 w-3" />
                        <span>Genera 3 Post AI su questo Trend</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="surface-panel overflow-hidden">
              <div className="border-b border-[var(--border-hairline)] px-4 py-3">
                <h2 className="text-[13px] font-semibold">Pain Point Reali Rilevati sui Tuoi Lead</h2>
                <p className="text-[12px] text-[var(--text-muted)]">
                  Criticità misurate direttamente nell&apos;archivio clienti (Zero Hallucination)
                </p>
              </div>
              <div className="divide-y divide-[var(--border-hairline)]">
                {trendsData?.pain_points.map((pp) => (
                  <div key={pp.id} className="p-3.5 space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[13px] font-semibold text-[var(--text-primary)]">{pp.title}</span>
                      <span className="rounded bg-amber-50 border border-amber-200 px-2 py-0.5 text-[11px] font-semibold text-amber-800 tabular-nums">
                        {formatNumber(pp.affected_count)} aziende ({pp.affected_pct}%)
                      </span>
                    </div>
                    <p className="text-[12px] text-[var(--text-muted)]">{pp.evidence}</p>
                    <div className="rounded bg-[var(--bg-subtle)] p-2 text-[12px] text-[var(--text-secondary)]">
                      <strong>Angolo Social:</strong> {pp.social_angle}
                    </div>
                    <div className="pt-1 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => sendTopicToSocialAI(pp.social_angle)}
                        className="inline-flex items-center gap-1 rounded border border-[#1D4ED8] px-2.5 py-1 text-[11px] font-medium text-[#1D4ED8] hover:bg-blue-50"
                      >
                        <Sparkles className="h-3 w-3" />
                        <span>Crea 3 Post su questo Pain Point</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {trendsData && (
            <div className="surface-panel p-4 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Hash className="h-4 w-4 text-[#1D4ED8]" />
                  <h2 className="text-[13px] font-semibold">Keyword &amp; Hashtag da Attaccare ai Post</h2>
                </div>
                <button
                  type="button"
                  onClick={() => copyText("all_hashtags", trendsData.hashtags.join(" "))}
                  className="inline-flex items-center gap-1 rounded border border-[var(--border-hairline)] px-2.5 py-1 text-[11px] font-medium hover:bg-[var(--bg-subtle)]"
                >
                  {copiedKey === "all_hashtags" ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                  <span>Copia tutti gli Hashtag</span>
                </button>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {trendsData.hashtags.map((h) => (
                  <button
                    key={h}
                    type="button"
                    onClick={() => copyText(h, h)}
                    className="rounded border border-blue-200 bg-blue-50/60 px-2 py-0.5 font-mono text-[11px] text-[#1D4ED8] hover:bg-blue-100"
                  >
                    {copiedKey === h ? "Copiato!" : h}
                  </button>
                ))}
              </div>
              <div className="pt-1 flex flex-wrap items-center gap-2 text-[12px]">
                <span className="font-medium text-[var(--text-secondary)]">Keyword SEO locali:</span>
                {trendsData.seo_keywords.map((kw) => (
                  <span
                    key={kw}
                    className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2 py-0.5 text-[11px]"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "fb_leads" && (
        <div className="space-y-4">
          {fbMeta && !fbMeta.serper_active && !fbMeta.fb_token_active && (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50/70 px-3.5 py-2.5 text-[12px] text-amber-900">
              <AlertCircle className="h-4 w-4 shrink-0 text-amber-700 mt-0.5" />
              <span>
                Modalità <strong>Archivio Locale</strong> attiva: per leggere automaticamente i post pubblici delle pagine Facebook dei lead, aggiungi{" "}
                <code className="font-mono">SERPER_API_KEY</code> o <code className="font-mono">FACEBOOK_ACCESS_TOKEN</code> nel file <code className="font-mono">.env</code>.
              </span>
            </div>
          )}

          <div className="surface-panel overflow-hidden">
            <div className="border-b border-[var(--border-hairline)] px-4 py-3 flex items-center justify-between">
              <div>
                <h2 className="text-[13px] font-semibold">Monitoraggio Pagine Facebook dei Lead</h2>
                <p className="text-[12px] text-[var(--text-muted)]">
                  Verifica quali aziende pubblicano, che temi trattano e come agganciarle
                </p>
              </div>
              <button
                type="button"
                onClick={loadFbLeads}
                className="flex h-8 items-center gap-1 rounded border border-[var(--border-hairline)] px-3 text-[12px] font-medium hover:bg-[var(--bg-subtle)]"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${fbLoading ? "animate-spin" : ""}`} />
                <span>Analizza Batch</span>
              </button>
            </div>
            <div className="divide-y divide-[var(--border-hairline)]">
              {fbLoading && <div className="p-4 text-[12px] text-[var(--text-muted)]">Analisi pagine Facebook in corso...</div>}
              {!fbLoading &&
                fbItems.map((item, idx) => (
                  <div key={`${item.lead_id}-${idx}`} className="p-4 space-y-2">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <span className="text-[13px] font-semibold text-[var(--text-primary)]">{item.company_name}</span>
                        <span className="ml-2 text-[12px] text-[var(--text-muted)]">
                          {item.city} · {item.niche}
                        </span>
                      </div>
                      <span className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2 py-0.5 text-[11px]">
                        {item.status_label}
                      </span>
                    </div>
                    {item.facebook_url && (
                      <a
                        href={item.facebook_url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-[12px] text-[#1D4ED8] hover:underline"
                      >
                        <span>{item.facebook_url}</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                    {item.post_snippets.length > 0 && (
                      <div className="rounded bg-[var(--bg-subtle)] p-2.5 text-[12px] space-y-1">
                        {item.post_snippets.map((s, si) => (
                          <p key={si} className="text-[var(--text-secondary)]">
                            • {s}
                          </p>
                        ))}
                      </div>
                    )}
                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                      <div className="flex flex-wrap gap-1.5">
                        {item.detected_themes.map((th) => (
                          <span key={th} className="rounded bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-[#1D4ED8]">
                            {th}
                          </span>
                        ))}
                      </div>
                      <button
                        type="button"
                        onClick={() => sendTopicToSocialAI(`${item.company_name} (${item.city}): ${item.suggested_hook}`)}
                        className="inline-flex items-center gap-1 text-[11px] font-medium text-[#1D4ED8] hover:underline"
                      >
                        <Sparkles className="h-3 w-3" />
                        <span>Crea Post su questo spunto</span>
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === "sector_news" && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            {[
              { id: "all", label: "Tutte le Opportunità" },
              { id: "bandi_pnrr", label: "Bandi, PNRR & Finanziamenti" },
              { id: "fiere_eventi", label: "Fiere, Eventi & Manifestazioni" },
              { id: "tecnologia_norme", label: "Novità Tecnologiche & Normative" },
            ].map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setNewsCategory(c.id)}
                className={`h-8 rounded-md px-3 text-[12px] font-medium border ${
                  newsCategory === c.id
                    ? "border-[#1D4ED8] bg-blue-50 text-[#1D4ED8]"
                    : "border-[var(--border-hairline)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]"
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>

          <div className="surface-panel divide-y divide-[var(--border-hairline)]">
            {newsLoading && <div className="p-4 text-[12px] text-[var(--text-muted)]">Ricerca bandi, fiere e novità dal web...</div>}
            {!newsLoading && newsItems.length === 0 && (
              <div className="p-4 text-[12px] text-[var(--text-muted)]">Nessuna notizia trovata per i filtri selezionati.</div>
            )}
            {newsItems.map((n) => (
              <div key={n.id} className="p-4 space-y-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="rounded bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[10px] font-semibold uppercase text-emerald-800">
                    {n.category_label}
                  </span>
                  <span className="text-[11px] text-[var(--text-muted)]">
                    {n.source} · {n.published_at}
                  </span>
                </div>
                <a
                  href={n.url}
                  target="_blank"
                  rel="noreferrer"
                  className="block text-[14px] font-semibold text-[#1D4ED8] hover:underline"
                >
                  {n.title}
                </a>
                <div className="rounded bg-[var(--bg-subtle)] p-2.5 text-[12px] text-[var(--text-secondary)] flex items-start gap-2">
                  <PhoneCall className="h-4 w-4 shrink-0 text-[#1D4ED8] mt-0.5" />
                  <div>
                    <span className="font-semibold text-[var(--text-primary)]">Script Telefonico 30s sul Bando: </span>
                    {n.phone_script_30s}
                  </div>
                </div>
                <div className="pt-1 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => sendTopicToSocialAI(n.title)}
                    className="inline-flex items-center gap-1 rounded border border-[#1D4ED8] px-2.5 py-1 text-[11px] font-medium text-[#1D4ED8] hover:bg-blue-50"
                  >
                    <Sparkles className="h-3 w-3" />
                    <span>Trasforma in 3 Post Social</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => copyText(n.id, n.phone_script_30s)}
                    className="inline-flex items-center gap-1 rounded border border-[var(--border-hairline)] px-2.5 py-1 text-[11px] font-medium hover:bg-[var(--bg-subtle)]"
                  >
                    {copiedKey === n.id ? <Check className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                    <span>Copia Script Chiamata</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === "social_ai" && (
        <div className="space-y-4">
          <div className="surface-panel p-4 space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div className="md:col-span-2">
                <label className="block text-[11px] font-semibold uppercase text-[var(--text-muted)] mb-1">
                  Argomento / Trend / Bando su cui scrivere i 3 post
                </label>
                <input
                  type="text"
                  value={socialTopic}
                  onChange={(e) => setSocialTopic(e.target.value)}
                  className="w-full h-9 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[13px]"
                />
              </div>
              <div>
                <label className="block text-[11px] font-semibold uppercase text-[var(--text-muted)] mb-1">
                  Tono di Voce
                </label>
                <select
                  value={socialTone}
                  onChange={(e) => setSocialTone(e.target.value)}
                  className="w-full h-9 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px]"
                >
                  <option>Tecnico-Pratico (da cantiere)</option>
                  <option>Istituzionale CNA Catania</option>
                  <option>Diretto &amp; Provocatorio (ROI)</option>
                </select>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <input
                type="text"
                value={socialInstruction}
                onChange={(e) => setSocialInstruction(e.target.value)}
                placeholder="Istruzione opzionale per rigenerare (es. 'rendilo più breve', 'cita il Bollino Blu')..."
                className="flex-1 min-w-[240px] h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px]"
              />
              <button
                type="button"
                disabled={socialBusy !== null}
                onClick={() => generatePosts()}
                className="flex h-8 items-center gap-1.5 rounded bg-[#1D4ED8] px-4 text-[12px] font-medium text-white hover:bg-blue-800 disabled:opacity-50"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>{socialBusy === "all" ? "Generazione in corso..." : "Genera Tutti e 3 i Post"}</span>
              </button>
            </div>
          </div>

          {socialBundle && (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {(
                  [
                    { key: "facebook", label: "Facebook (Community & Artigiani)", badgeColor: "bg-blue-50 text-blue-800 border-blue-200" },
                    { key: "instagram", label: "Instagram (Caption & Carosello)", badgeColor: "bg-pink-50 text-pink-800 border-pink-200" },
                    { key: "linkedin", label: "LinkedIn (B2B & Aziende)", badgeColor: "bg-sky-50 text-sky-900 border-sky-200" },
                  ] as Array<{ key: PlatformKey; label: string; badgeColor: string }>
                ).map((plat) => {
                  const post = socialBundle[plat.key];
                  return (
                    <div key={plat.key} className="surface-panel p-4 flex flex-col justify-between space-y-3">
                      <div className="space-y-2.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className={`rounded border px-2 py-0.5 text-[11px] font-semibold ${plat.badgeColor}`}>
                            {plat.label}
                          </span>
                          <button
                            type="button"
                            disabled={socialBusy !== null}
                            onClick={() => generatePosts(plat.key)}
                            className="inline-flex items-center gap-1 rounded border border-[var(--border-hairline)] px-2 py-1 text-[11px] font-medium hover:bg-[var(--bg-subtle)]"
                          >
                            <RefreshCw className={`h-3 w-3 ${socialBusy === plat.key ? "animate-spin" : ""}`} />
                            <span>Rigenera</span>
                          </button>
                        </div>

                        <textarea
                          rows={9}
                          value={post.text}
                          onChange={(e) =>
                            setSocialBundle({
                              ...socialBundle,
                              [plat.key]: { ...post, text: e.target.value },
                            })
                          }
                          className="w-full rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] p-2.5 text-[12px] leading-relaxed"
                        />

                        <div className="rounded border border-dashed border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-2.5 space-y-1">
                          <div className="flex items-center justify-between">
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[var(--text-secondary)]">
                              <ImageIcon className="h-3.5 w-3.5 text-[#1D4ED8]" />
                              Prompt Immagine (da usare fuori)
                            </span>
                            <button
                              type="button"
                              onClick={() => copyText(`img-${plat.key}`, post.image_prompt)}
                              className="text-[11px] text-[#1D4ED8] hover:underline"
                            >
                              {copiedKey === `img-${plat.key}` ? "Copiato!" : "Copia Prompt"}
                            </button>
                          </div>
                          <p className="text-[11px] text-[var(--text-muted)] leading-snug">{post.image_prompt}</p>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => copyText(`post-${plat.key}`, `${post.text}\n\n${socialBundle.hashtags.join(" ")}`)}
                        className="w-full h-8 flex items-center justify-center gap-1.5 rounded border border-[#1D4ED8] text-[12px] font-medium text-[#1D4ED8] hover:bg-blue-50"
                      >
                        {copiedKey === `post-${plat.key}` ? (
                          <>
                            <Check className="h-3.5 w-3.5 text-emerald-600" />
                            <span>Testo + Hashtag Copiati!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" />
                            <span>Copia Post + Hashtag</span>
                          </>
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>

              <div className="surface-panel p-3.5 flex flex-wrap items-center justify-between gap-2 text-[12px]">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="font-semibold">Hashtag:</span>
                  <span className="font-mono text-[11px] text-[#1D4ED8]">{socialBundle.hashtags.join(" ")}</span>
                </div>
                <span className="text-[11px] text-[var(--text-muted)]">
                  Motore: {socialBundle.generated_by} (Bozza HITL — nessuna pubblicazione automatica)
                </span>
              </div>
            </>
          )}
        </div>
      )}

      {activeTab === "lead_demand" && (
        <div className="space-y-5">
          {legacyData && (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50/70 px-3.5 py-2.5 text-[12px] text-amber-900">
              <AlertCircle className="h-4 w-4 shrink-0 text-amber-700 mt-0.5" />
              <span>{legacyData.disclaimer}</span>
            </div>
          )}

          {signals && (
            <div className="surface-panel grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-[var(--border-hairline)]">
              <Link
                href={`/leads?search_id=${encodeURIComponent(searchId)}&view=callable_ab`}
                className="px-4 py-3.5 hover:bg-[var(--bg-subtle)] transition-colors"
              >
                <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
                  Senza Reperibilità H24 (Dati Reali)
                </div>
                <div className="mt-1 text-[20px] font-semibold tabular-nums text-[var(--text-primary)]">
                  {formatNumber(signals.office_hours_no_h24)}
                </div>
                <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">Target prioritario centralino AI H24</div>
              </Link>

              <Link
                href={`/leads?search_id=${encodeURIComponent(searchId)}`}
                className="px-4 py-3.5 hover:bg-[var(--bg-subtle)] transition-colors"
              >
                <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
                  Non Associate CNA (Leva 50%)
                </div>
                <div className="mt-1 text-[20px] font-semibold tabular-nums text-[var(--text-primary)]">
                  {formatNumber(signals.cna_non_associated)}
                </div>
                <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">Eleggibili quota CNA Catania 50% 1° anno</div>
              </Link>

              <div className="px-4 py-3.5">
                <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
                  Specialisti Marchi Verificati
                </div>
                <div className="mt-1 text-[20px] font-semibold tabular-nums text-[var(--text-primary)]">
                  {formatNumber(signals.verified_brand_specialists)}
                </div>
                <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">Vaillant, Daikin, Bosch, Mitsubishi, ecc.</div>
              </div>

              <Link
                href={`/leads?search_id=${encodeURIComponent(searchId)}&view=to_enrich`}
                className="px-4 py-3.5 hover:bg-[var(--bg-subtle)] transition-colors"
              >
                <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
                  Senza Telefono (Coda Enrichment)
                </div>
                <div className="mt-1 text-[20px] font-semibold tabular-nums text-[var(--text-primary)]">
                  {formatNumber(signals.to_enrich_no_phone)}
                </div>
                <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">Arricchibili via Places API / Openapi</div>
              </Link>
            </div>
          )}

          {legacyData && <SeasonalityTrendChart data={legacyData.seasonality_12m} />}

          {legacyData && signals && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div className="surface-panel overflow-hidden">
                <div className="border-b border-[var(--border-hairline)] px-4 py-3">
                  <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
                    Driver Normativi &amp; Convenzione CNA Catania
                  </h2>
                </div>
                <div className="divide-y divide-[var(--border-hairline)]">
                  {legacyData.regulatory_drivers.map((drv) => {
                    const isOpen = openDriver === drv.id;
                    return (
                      <div key={drv.id}>
                        <button
                          type="button"
                          onClick={() => setOpenDriver(isOpen ? "" : drv.id)}
                          className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left hover:bg-[var(--bg-subtle)]"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="rounded border border-blue-200 bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-[#1D4ED8]">
                              {drv.badge}
                            </span>
                            <span className="truncate text-[13px] font-medium text-[var(--text-primary)]">{drv.title}</span>
                          </div>
                          <ChevronDown
                            className={`h-4 w-4 text-[var(--text-muted)] transition-transform ${isOpen ? "rotate-180" : ""}`}
                          />
                        </button>
                        {isOpen && (
                          <div className="bg-[var(--bg-subtle)] px-4 py-3 text-[12px] leading-relaxed text-[var(--text-secondary)]">
                            {drv.summary}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="surface-panel p-4">
                <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
                  Top Marchi Verificati nel Dataset ({formatNumber(signals.total_analyzed)} imprese)
                </h2>
                <div className="mt-2.5 flex flex-wrap gap-1.5">
                  {signals.top_brands.map((b) => (
                    <span
                      key={b.brand}
                      className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2 py-1 text-[12px] tabular-nums"
                    >
                      <strong className="font-medium text-[var(--text-primary)]">{b.brand}</strong>{" "}
                      <span className="text-[var(--text-muted)]">({b.count})</span>
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
