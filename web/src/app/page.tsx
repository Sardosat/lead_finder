"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Download, Plus, TableProperties } from "lucide-react";
import { GeoCoverageChart } from "@/components/charts/GeoCoverageChart";
import { ProductTierChart } from "@/components/charts/ProductTierChart";
import { QualityFunnelChart } from "@/components/charts/QualityFunnelChart";
import { api } from "@/lib/api";
import { APPROVAL_BADGE, formatBytes, formatDateIT, formatNumber } from "@/lib/formatters";
import type { OverviewResponse, SavedSearch } from "@/lib/types";

export default function PanoramicaPage() {
  const [searchId, setSearchId] = useState("ds-master-clean");
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getSearches()
      .then((res) => {
        const usable = res.searches.filter((s) => s.leads_count > 0);
        setSearches(usable);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    api
      .getOverview(searchId)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Errore caricamento panoramica.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [searchId]);

  const kpis = data?.kpis;

  return (
    <div className="space-y-5 max-w-[1440px]">
      {/* Page Action Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5 min-w-0 w-full sm:w-auto">
          <label htmlFor="overview-ds" className="text-[12px] font-medium text-[var(--text-secondary)] shrink-0">
            Lista analizzata:
          </label>
          <select
            id="overview-ds"
            value={searchId}
            onChange={(e) => setSearchId(e.target.value)}
            className="h-8 max-w-full min-w-0 flex-1 sm:flex-initial truncate rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px] font-medium text-[var(--text-primary)] focus:border-[#1D4ED8] focus:outline-none"
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

        <div className="flex items-center gap-2">
          <Link
            href={`/leads?search_id=${encodeURIComponent(searchId)}`}
            className="flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[12px] font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] transition-colors"
          >
            <TableProperties className="h-3.5 w-3.5 text-[var(--text-muted)]" />
            <span>Apri in Lead Finder</span>
          </Link>
          <Link
            href="/ricerca/nuova"
            className="flex h-8 items-center gap-1.5 rounded-md bg-[#1D4ED8] px-3 text-[12px] font-medium text-white hover:bg-[#1E40AF] transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Nuova Ricerca</span>
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3.5 py-2.5 text-[13px] text-red-700">
          {error}
        </div>
      )}

      {/* Flat Single-Row KPI Strip (Zero Tile Soup) */}
      <div className="surface-panel grid grid-cols-2 md:grid-cols-5 divide-y md:divide-y-0 md:divide-x divide-[var(--border-hairline)]">
        <div className="px-4 py-3.5">
          <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
            Lead Puliti
          </div>
          <div className="mt-1 text-[22px] font-semibold tracking-tight tabular-nums text-[var(--text-primary)]">
            {loading || !kpis ? "—" : formatNumber(kpis.total_leads)}
          </div>
          <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">
            Score medio {kpis ? `${kpis.avg_icp_score}/100` : "—"}
          </div>
        </div>

        <div className="px-4 py-3.5">
          <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
            Chiamabili E.164
          </div>
          <div className="mt-1 text-[22px] font-semibold tracking-tight tabular-nums text-[var(--text-primary)]">
            {loading || !kpis ? "—" : formatNumber(kpis.callable_e164)}
          </div>
          <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">
            {kpis && kpis.total_leads
              ? `${((kpis.callable_e164 / kpis.total_leads) * 100).toFixed(1)}% pronti chiamata`
              : "—"}
          </div>
        </div>

        <div className="px-4 py-3.5">
          <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
            P.IVA Luhn Valide
          </div>
          <div className="mt-1 text-[22px] font-semibold tracking-tight tabular-nums text-[var(--text-primary)]">
            {loading || !kpis ? "—" : formatNumber(kpis.valid_piva)}
          </div>
          <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">
            {kpis ? `${formatNumber(kpis.cna_eligible)} eleggibili CNA 50%` : "—"}
          </div>
        </div>

        <div className="px-4 py-3.5">
          <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
            Tier A + B Pronti
          </div>
          <div className="mt-1 text-[22px] font-semibold tracking-tight tabular-nums text-[var(--text-primary)]">
            {loading || !kpis ? "—" : formatNumber(kpis.tier_a_b)}
          </div>
          <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">
            {kpis ? `${formatNumber(kpis.tier_a)} VIP Tier A` : "—"}
          </div>
        </div>

        <div className="px-4 py-3.5 col-span-2 md:col-span-1">
          <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
            Export in Archivio
          </div>
          <div className="mt-1 text-[22px] font-semibold tracking-tight tabular-nums text-[var(--text-primary)]">
            {loading || !kpis ? "—" : formatNumber(kpis.exports_count)}
          </div>
          <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">
            {kpis ? `${formatNumber(kpis.searches_count)} ricerche/playbook` : "—"}
          </div>
        </div>
      </div>

      {/* Charts Row 1: Quality Funnel + Ecosystem Product Routing */}
      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <QualityFunnelChart data={data.quality_funnel} />
          <ProductTierChart data={data.product_tier_matrix} />
        </div>
      )}

      {/* Charts Row 2: Territorial & Niche Coverage */}
      {data && (
        <GeoCoverageChart geoData={data.geo_coverage} nicheData={data.niche_coverage} />
      )}

      {/* Bottom Compact Lists: Recent Searches & Recent Exports */}
      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Ultime Ricerche */}
          <div className="surface-panel overflow-hidden">
            <div className="flex items-center justify-between border-b border-[var(--border-hairline)] px-4 py-2.5">
              <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
                Le mie Ricerche &amp; Archivi
              </h2>
              <Link
                href="/ricerche"
                className="flex items-center gap-1 text-[12px] font-medium text-[var(--accent)] hover:underline"
              >
                <span>Vedi tutte</span>
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="divide-y divide-[var(--border-hairline)]">
              {data.recent_searches.map((s) => (
                <Link
                  key={s.id}
                  href={`/leads?search_id=${encodeURIComponent(s.id)}`}
                  className="flex items-center justify-between gap-3 px-4 py-2.5 hover:bg-[var(--bg-subtle)] transition-colors"
                >
                  <div className="min-w-0">
                    <div className="truncate text-[13px] font-medium text-[var(--text-primary)]">
                      {s.name}
                    </div>
                    <div className="truncate text-[11px] text-[var(--text-muted)]">
                      {s.target_vertical} · {s.source_type === "dataset" ? "Archivio" : s.source_type === "preset" ? "Playbook" : "Custom"}
                    </div>
                  </div>
                  <div className="text-right shrink-0 tabular-nums">
                    <div className="text-[12px] font-medium text-[var(--text-primary)]">
                      {formatNumber(s.leads_count)} lead
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)]">
                      {formatNumber(s.callable_count)} chiamabili
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {/* Ultimi Export */}
          <div className="surface-panel overflow-hidden">
            <div className="flex items-center justify-between border-b border-[var(--border-hairline)] px-4 py-2.5">
              <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
                Ultimi Export Salvati
              </h2>
              <Link
                href="/exports"
                className="flex items-center gap-1 text-[12px] font-medium text-[var(--accent)] hover:underline"
              >
                <span>Archivio completo</span>
                <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
            <div className="divide-y divide-[var(--border-hairline)]">
              {data.recent_exports.map((exp) => {
                const badge = APPROVAL_BADGE[exp.approval_status] || APPROVAL_BADGE.DRAFT;
                return (
                  <div
                    key={exp.id}
                    className="flex items-center justify-between gap-3 px-4 py-2.5 hover:bg-[var(--bg-subtle)] transition-colors"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-[13px] font-medium text-[var(--text-primary)]">
                        {exp.filename}
                      </div>
                      <div className="truncate text-[11px] text-[var(--text-muted)]">
                        {exp.format} · {formatBytes(exp.size_bytes)} · {formatDateIT(exp.created_at)}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${badge.className}`}
                      >
                        {badge.label}
                      </span>
                      <a
                        href={api.getExportDownloadUrl(exp.id)}
                        title="Scarica file"
                        className="flex h-7 w-7 items-center justify-center rounded border border-[var(--border-hairline)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface)] hover:text-[var(--text-primary)]"
                      >
                        <Download className="h-3.5 w-3.5" />
                      </a>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
