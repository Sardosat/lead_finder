"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, ArrowUpRight, Check, ChevronDown, Copy } from "lucide-react";
import { SeasonalityTrendChart } from "@/components/charts/SeasonalityTrendChart";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/formatters";
import type { SavedSearch, TrendsResponse } from "@/lib/types";

export default function TrendFinderPage() {
  const [searchId, setSearchId] = useState("ds-master-clean");
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [data, setData] = useState<TrendsResponse | null>(null);
  const [openDriver, setOpenDriver] = useState<string>("cna-50");
  const [copiedKw, setCopiedKw] = useState("");

  useEffect(() => {
    api
      .getSearches()
      .then((res) => setSearches(res.searches.filter((s) => s.leads_count > 0)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    api.getTrends(searchId).then(setData).catch(() => {});
  }, [searchId]);

  const copyKeyword = async (kw: string) => {
    try {
      await navigator.clipboard.writeText(kw);
      setCopiedKw(kw);
      setTimeout(() => setCopiedKw(""), 1500);
    } catch {
      // ignore
    }
  };

  const signals = data?.real_intent_signals;

  return (
    <div className="space-y-5 max-w-[1440px]">
      {/* Dataset selector + STIMA TEORICA disclosure */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5 min-w-0 w-full sm:w-auto">
          <span className="text-[12px] font-medium text-[var(--text-secondary)] shrink-0">Archivio di riferimento:</span>
          <select
            value={searchId}
            onChange={(e) => setSearchId(e.target.value)}
            className="h-8 max-w-full min-w-0 flex-1 sm:flex-initial truncate rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px] font-medium"
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

        <Link
          href={`/leads?search_id=${encodeURIComponent(searchId)}`}
          className="flex h-8 items-center gap-1 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[12px] font-medium hover:bg-[var(--bg-subtle)]"
        >
          <span>Esplora i target nel Lead Finder</span>
          <ArrowUpRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      {data && (
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50/70 px-3.5 py-2.5 text-[12px] text-amber-900">
          <AlertCircle className="h-4 w-4 shrink-0 text-amber-700 mt-0.5" />
          <span>{data.disclaimer}</span>
        </div>
      )}

      {/* Real Signals Flat KPI Strip */}
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
            <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">
              Target prioritario centralino AI H24
            </div>
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
            <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">
              Eleggibili quota CNA Catania 50% 1° anno
            </div>
          </Link>

          <div className="px-4 py-3.5">
            <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
              Specialisti Marchi Verificati
            </div>
            <div className="mt-1 text-[20px] font-semibold tabular-nums text-[var(--text-primary)]">
              {formatNumber(signals.verified_brand_specialists)}
            </div>
            <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">
              Vaillant, Daikin, Bosch, Mitsubishi, ecc.
            </div>
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
            <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">
              Arricchibili via Places API / Openapi
            </div>
          </Link>
        </div>
      )}

      {/* 12-Month Seasonality Chart */}
      {data && <SeasonalityTrendChart data={data.seasonality_12m} />}

      {/* Lower 2-Column Workspace: Regulatory Drivers + Real Top Brands & Keywords */}
      {data && signals && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Driver Normativi Accordion */}
          <div className="surface-panel overflow-hidden">
            <div className="border-b border-[var(--border-hairline)] px-4 py-3">
              <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
                Driver Normativi &amp; Convenzione CNA Catania
              </h2>
              <p className="text-[12px] text-[var(--text-muted)]">
                Leve concrete d&apos;urgenza normativa per l&apos;apertura commerciale
              </p>
            </div>
            <div className="divide-y divide-[var(--border-hairline)]">
              {data.regulatory_drivers.map((drv) => {
                const isOpen = openDriver === drv.id;
                return (
                  <div key={drv.id}>
                    <button
                      type="button"
                      onClick={() => setOpenDriver(isOpen ? "" : drv.id)}
                      className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left hover:bg-[var(--bg-subtle)]"
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="rounded border border-blue-200 bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-[#1D4ED8]">
                            {drv.badge}
                          </span>
                          <span className="truncate text-[13px] font-medium text-[var(--text-primary)]">
                            {drv.title}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[11px] tabular-nums text-[var(--text-muted)]">
                          {formatNumber(drv.target_count)} target
                        </span>
                        <ChevronDown
                          className={`h-4 w-4 text-[var(--text-muted)] transition-transform ${
                            isOpen ? "rotate-180" : ""
                          }`}
                        />
                      </div>
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

          {/* Right Col: Real Brands + Keyword Clusters */}
          <div className="space-y-4">
            <div className="surface-panel p-4">
              <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
                Top Marchi Verificati nel Dataset ({formatNumber(signals.total_analyzed)} imprese)
              </h2>
              <div className="mt-2.5 flex flex-wrap gap-1.5">
                {signals.top_brands.length === 0 ? (
                  <span className="text-[12px] text-[var(--text-muted)]">Nessun marchio estratto in questa lista.</span>
                ) : (
                  signals.top_brands.map((b) => (
                    <span
                      key={b.brand}
                      className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2 py-1 text-[12px] tabular-nums"
                    >
                      <strong className="font-medium text-[var(--text-primary)]">{b.brand}</strong>{" "}
                      <span className="text-[var(--text-muted)]">({b.count})</span>
                    </span>
                  ))
                )}
              </div>
            </div>

            <div className="surface-panel overflow-hidden">
              <div className="border-b border-[var(--border-hairline)] px-4 py-2.5">
                <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
                  Cluster Keyword di Ricerca Locale (Clicca per copiare)
                </h2>
              </div>
              <div className="divide-y divide-[var(--border-hairline)]">
                {data.keyword_clusters.map((cl) => (
                  <div key={cl.cluster} className="px-4 py-2.5">
                    <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)] mb-1.5">
                      {cl.cluster}
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {cl.keywords.map((kw) => (
                        <button
                          key={kw}
                          type="button"
                          onClick={() => copyKeyword(kw)}
                          className="inline-flex items-center gap-1 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2 py-0.5 font-mono text-[11px] text-[var(--text-secondary)] hover:border-[#1D4ED8] hover:text-[#1D4ED8]"
                        >
                          <span>{kw}</span>
                          {copiedKw === kw ? (
                            <Check className="h-3 w-3 text-emerald-600" />
                          ) : (
                            <Copy className="h-2.5 w-2.5 opacity-50" />
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
