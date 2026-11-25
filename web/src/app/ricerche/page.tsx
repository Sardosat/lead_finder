"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Copy, ExternalLink, Play, Plus, RefreshCw, Search, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { formatDateIT, formatEur, formatNumber, PRODUCT_BADGE } from "@/lib/formatters";
import type { SavedSearch } from "@/lib/types";

export default function RicerchePage() {
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [sourceFilter, setSourceFilter] = useState<"all" | "dataset" | "custom" | "preset">("all");
  const [q, setQ] = useState("");
  const [busyId, setBusyId] = useState("");
  const [msg, setMsg] = useState("");

  const loadSearches = useCallback(async () => {
    try {
      const res = await api.getSearches();
      setSearches(res.searches);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSearches();
  }, [loadSearches]);

  // Poll cleanly only while any search is running
  useEffect(() => {
    const hasRunning = searches.some((s) => s.status === "running");
    if (!hasRunning) return;
    const iv = setInterval(() => {
      loadSearches();
    }, 2000);
    return () => clearInterval(iv);
  }, [searches, loadSearches]);

  const filtered = useMemo(() => {
    return searches.filter((s) => {
      if (sourceFilter !== "all" && s.source_type !== sourceFilter) return false;
      if (q.trim()) {
        const ql = q.trim().toLowerCase();
        return (
          s.name.toLowerCase().includes(ql) ||
          s.target_vertical.toLowerCase().includes(ql) ||
          s.ateco_codes.join(",").toLowerCase().includes(ql)
        );
      }
      return true;
    });
  }, [searches, sourceFilter, q]);

  const handleRun = async (id: string) => {
    setBusyId(id);
    setMsg("");
    try {
      await api.runSearch(id);
      await loadSearches();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Errore avvio pipeline.");
    } finally {
      setBusyId("");
    }
  };

  const handleDuplicate = async (id: string) => {
    setBusyId(id);
    try {
      await api.duplicateSearch(id);
      await loadSearches();
    } finally {
      setBusyId("");
    }
  };

  const handleDelete = async (id: string) => {
    setBusyId(id);
    setMsg("");
    try {
      await api.deleteSearch(id);
      await loadSearches();
    } catch (err) {
      setMsg(err instanceof Error ? err.message : "Errore eliminazione.");
    } finally {
      setBusyId("");
    }
  };

  return (
    <div className="space-y-4 max-w-[1440px]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { id: "all", label: `Tutte (${searches.length})` },
            { id: "dataset", label: "Archivi Attivi" },
            { id: "custom", label: "Le mie Ricerche" },
            { id: "preset", label: "Playbook Multi-Settore" },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setSourceFilter(tab.id as "all" | "dataset" | "custom" | "preset")}
              className={`rounded-md px-2.5 py-1.5 text-[12px] font-medium transition-colors ${
                sourceFilter === tab.id
                  ? "bg-[var(--accent-tint)] text-[#1D4ED8]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[var(--text-muted)]" />
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Filtra ricerche o ATECO..."
              className="h-8 w-56 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] pl-8 pr-2.5 text-[12px] focus:border-[#1D4ED8] focus:outline-none"
            />
          </div>
          <Link
            href="/ricerca/nuova"
            className="flex h-8 items-center gap-1.5 rounded-md bg-[#1D4ED8] px-3 text-[12px] font-medium text-white hover:bg-[#1E40AF]"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Nuova Ricerca</span>
          </Link>
        </div>
      </div>

      {msg && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-[12px] text-amber-800">
          {msg}
        </div>
      )}

      <div className="surface-panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead className="border-b border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
              <tr>
                <th className="px-4 py-2.5">Ricerca / Archivio</th>
                <th className="px-3 py-2.5">Territorio &amp; ATECO</th>
                <th className="px-3 py-2.5">Prodotto Target</th>
                <th className="px-3 py-2.5">Lead / Chiamabili</th>
                <th className="px-3 py-2.5">Stato</th>
                <th className="px-3 py-2.5">Costo €</th>
                <th className="px-3 py-2.5">Ultimo Run</th>
                <th className="px-4 py-2.5 text-right">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-hairline)] text-[13px]">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-[var(--text-muted)]">
                    Caricamento ricerche...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-[var(--text-muted)]">
                    Nessuna ricerca corrispondente.
                  </td>
                </tr>
              ) : (
                filtered.map((s) => {
                  const pBadge = PRODUCT_BADGE[s.product_target] || PRODUCT_BADGE.rsksystem;
                  const munis = s.geo?.municipalities?.slice(0, 3).join(", ") || "Italia";
                  return (
                    <tr key={s.id} className="hover:bg-[var(--bg-subtle)] transition-colors">
                      <td className="px-4 py-3 max-w-[320px]">
                        <div className="flex items-center gap-2">
                          <span className="truncate font-medium text-[var(--text-primary)]">{s.name}</span>
                          <span className="shrink-0 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-1.5 py-0.5 text-[10px] font-medium uppercase text-[var(--text-muted)]">
                            {s.source_type === "dataset"
                              ? "Archivio"
                              : s.source_type === "preset"
                                ? "Playbook"
                                : "Custom"}
                          </span>
                        </div>
                        <div className="truncate text-[11px] text-[var(--text-muted)] mt-0.5">
                          {s.target_vertical}
                        </div>
                      </td>

                      <td className="px-3 py-3 text-[12px]">
                        <div className="text-[var(--text-primary)] truncate max-w-[200px]">{munis}</div>
                        <div className="font-mono text-[11px] text-[var(--text-muted)] truncate max-w-[200px]">
                          {s.ateco_codes.length > 0 ? `ATECO ${s.ateco_codes.slice(0, 3).join(", ")}` : "Multi-ATECO"}
                        </div>
                      </td>

                      <td className="px-3 py-3">
                        <span className={`rounded border px-1.5 py-0.5 text-[11px] font-medium ${pBadge.className}`}>
                          {pBadge.label}
                        </span>
                      </td>

                      <td className="px-3 py-3 tabular-nums">
                        <div className="font-medium text-[var(--text-primary)]">
                          {formatNumber(s.leads_count)}
                        </div>
                        <div className="text-[11px] text-[var(--text-muted)]">
                          {formatNumber(s.callable_count)} chiamabili
                        </div>
                      </td>

                      <td className="px-3 py-3 text-[12px]">
                        <span
                          className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-medium ${
                            s.status === "running"
                              ? "border-blue-200 bg-blue-50 text-blue-700"
                              : s.status === "failed"
                                ? "border-red-200 bg-red-50 text-red-700"
                                : s.status === "draft"
                                  ? "border-slate-200 bg-slate-100 text-slate-700"
                                  : "border-emerald-200 bg-emerald-50 text-emerald-700"
                          }`}
                        >
                          {s.status === "running" && <RefreshCw className="h-2.5 w-2.5 animate-spin" />}
                          <span>
                            {s.status === "running"
                              ? "In corso"
                              : s.status === "failed"
                                ? "Errore"
                                : s.status === "draft"
                                  ? "Bozza"
                                  : "Pronta"}
                          </span>
                        </span>
                        {s.status_note && (
                          <div className="mt-0.5 max-w-[180px] truncate text-[10px] text-[var(--text-muted)]" title={s.status_note}>
                            {s.status_note}
                          </div>
                        )}
                      </td>

                      <td className="px-3 py-3 tabular-nums text-[12px] text-[var(--text-secondary)]">
                        {s.cost_eur > 0 ? formatEur(s.cost_eur) : s.estimated_cost_eur > 0 ? `~${formatEur(s.estimated_cost_eur)}` : "€ 0,00"}
                      </td>

                      <td className="px-3 py-3 whitespace-nowrap text-[11px] text-[var(--text-muted)]">
                        {formatDateIT(s.last_run_at)}
                      </td>

                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex items-center gap-1">
                          {s.leads_count > 0 && (
                            <Link
                              href={`/leads?search_id=${encodeURIComponent(s.id)}`}
                              title="Apri in Lead Finder"
                              className="flex h-7 items-center gap-1 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[11px] font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                            >
                              <ExternalLink className="h-3 w-3" />
                              <span>Apri</span>
                            </Link>
                          )}
                          {s.source_type !== "dataset" && (
                            <button
                              type="button"
                              disabled={busyId === s.id || s.status === "running"}
                              onClick={() => handleRun(s.id)}
                              title="Esegui pipeline ricerca"
                              className="flex h-7 items-center gap-1 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[11px] font-medium text-[#1D4ED8] hover:bg-[var(--accent-tint)] disabled:opacity-40"
                            >
                              <Play className="h-3 w-3" />
                              <span>Esegui</span>
                            </button>
                          )}
                          <button
                            type="button"
                            disabled={busyId === s.id}
                            onClick={() => handleDuplicate(s.id)}
                            title="Duplica configurazione"
                            className="flex h-7 w-7 items-center justify-center rounded border border-[var(--border-hairline)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]"
                          >
                            <Copy className="h-3 w-3" />
                          </button>
                          {s.source_type === "custom" && (
                            <button
                              type="button"
                              disabled={busyId === s.id}
                              onClick={() => handleDelete(s.id)}
                              title="Elimina ricerca"
                              className="flex h-7 w-7 items-center justify-center rounded border border-[var(--border-hairline)] text-red-600 hover:bg-red-50"
                            >
                              <Trash2 className="h-3 w-3" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
