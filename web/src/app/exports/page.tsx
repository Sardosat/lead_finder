"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Download, Eye, Plus, Search, Trash2 } from "lucide-react";
import { ExportModal } from "@/components/exports/ExportModal";
import { ExportPreviewDrawer } from "@/components/exports/ExportPreviewDrawer";
import { api } from "@/lib/api";
import { APPROVAL_BADGE, formatBytes, formatDateIT, formatNumber } from "@/lib/formatters";
import type { ExportRecord, SavedSearch } from "@/lib/types";

export default function ArchivioExportPage() {
  const [exportsList, setExportsList] = useState<ExportRecord[]>([]);
  const [counts, setCounts] = useState({ total: 0, csv_xlsx: 0, webhook_json: 0, pdf: 0, markdown: 0 });
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [fmtFilter, setFmtFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [q, setQ] = useState("");
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [newSearchId, setNewSearchId] = useState("ds-outbound-tecnicolive");

  const loadExports = useCallback(async () => {
    try {
      const res = await api.getExports({
        format: fmtFilter || undefined,
        approval_status: statusFilter || undefined,
      });
      setExportsList(res.exports);
      setCounts(res.counts);
    } finally {
      setLoading(false);
    }
  }, [fmtFilter, statusFilter]);

  useEffect(() => {
    loadExports();
  }, [loadExports]);

  useEffect(() => {
    api
      .getSearches()
      .then((r) => setSearches(r.searches.filter((s) => s.leads_count > 0)))
      .catch(() => {});
  }, []);

  const filtered = useMemo(() => {
    const ql = q.trim().toLowerCase();
    if (!ql) return exportsList;
    return exportsList.filter(
      (e) =>
        e.filename.toLowerCase().includes(ql) ||
        e.search_name.toLowerCase().includes(ql) ||
        e.format.toLowerCase().includes(ql)
    );
  }, [exportsList, q]);

  const handleDelete = async (id: string) => {
    await api.deleteExport(id);
    loadExports();
  };

  const selectedSearchName = searches.find((s) => s.id === newSearchId)?.name || newSearchId;
  const selectedSearchCount = searches.find((s) => s.id === newSearchId)?.leads_count || 0;

  return (
    <div className="space-y-4 max-w-[1440px]">
      {/* Flat KPI Strip */}
      <div className="surface-panel grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-[var(--border-hairline)]">
        <div className="px-4 py-3">
          <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
            Totale Export Salvati
          </div>
          <div className="mt-1 text-[20px] font-semibold tabular-nums">{formatNumber(counts.total)}</div>
        </div>
        <div className="px-4 py-3">
          <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
            CSV &amp; Excel (.xlsx)
          </div>
          <div className="mt-1 text-[20px] font-semibold tabular-nums">{formatNumber(counts.csv_xlsx)}</div>
        </div>
        <div className="px-4 py-3">
          <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
            Bozze Webhook JSON
          </div>
          <div className="mt-1 text-[20px] font-semibold tabular-nums">{formatNumber(counts.webhook_json)}</div>
        </div>
        <div className="px-4 py-3">
          <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
            Report Strategici PDF
          </div>
          <div className="mt-1 text-[20px] font-semibold tabular-nums">{formatNumber(counts.pdf)}</div>
        </div>
      </div>

      {/* Filter & Generate Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[var(--text-muted)]" />
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Cerca file export..."
              className="h-8 w-52 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] pl-8 pr-2.5 text-[12px] focus:border-[#1D4ED8] focus:outline-none"
            />
          </div>

          <select
            value={fmtFilter}
            onChange={(e) => setFmtFilter(e.target.value)}
            className="h-8 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px]"
          >
            <option value="">Tutti i formati</option>
            <option value="CSV">CSV</option>
            <option value="XLSX">Excel (.xlsx)</option>
            <option value="WEBHOOK_JSON">Webhook JSON</option>
            <option value="PDF">PDF</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-8 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px]"
          >
            <option value="">Tutti gli stati HITL</option>
            <option value="DRAFT">Bozza HITL</option>
            <option value="APPROVED">Approvato</option>
            <option value="DISPATCHED">Inviato Webhook</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={newSearchId}
            onChange={(e) => setNewSearchId(e.target.value)}
            className="hidden sm:block h-8 max-w-[240px] rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px]"
          >
            {searches.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="flex h-8 items-center gap-1.5 rounded-md bg-[#1D4ED8] px-3 text-[12px] font-medium text-white hover:bg-[#1E40AF]"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Nuovo Export</span>
          </button>
        </div>
      </div>

      {/* Exports Table */}
      <div className="surface-panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left">
            <thead className="border-b border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">
              <tr>
                <th className="px-4 py-2.5">File</th>
                <th className="px-3 py-2.5">Formato</th>
                <th className="px-3 py-2.5">Origine / Ricerca</th>
                <th className="px-3 py-2.5">Righe (Escluse LIA)</th>
                <th className="px-3 py-2.5">Stato HITL</th>
                <th className="px-3 py-2.5">Dimensione</th>
                <th className="px-3 py-2.5">Data</th>
                <th className="px-4 py-2.5 text-right">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-hairline)] text-[13px]">
              {loading ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-[var(--text-muted)]">
                    Caricamento Archivio Export...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-10 text-center text-[var(--text-muted)]">
                    Nessun export salvato con i filtri attuali.
                  </td>
                </tr>
              ) : (
                filtered.map((exp) => {
                  const badge = APPROVAL_BADGE[exp.approval_status] || APPROVAL_BADGE.DRAFT;
                  return (
                    <tr key={exp.id} className="hover:bg-[var(--bg-subtle)] transition-colors">
                      <td className="px-4 py-3 max-w-[280px]">
                        <div className="truncate font-mono text-[12px] font-medium text-[var(--text-primary)]">
                          {exp.filename}
                        </div>
                        <div className="text-[11px] text-[var(--text-muted)]">
                          {exp.origin === "legacy" ? "Report / Storico Workspace" : "Generato da Console"}
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <span className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-1.5 py-0.5 font-mono text-[10px] font-semibold">
                          {exp.format}
                        </span>
                      </td>
                      <td className="px-3 py-3 max-w-[240px] truncate text-[12px] text-[var(--text-secondary)]">
                        {exp.search_name}
                      </td>
                      <td className="px-3 py-3 tabular-nums text-[12px]">
                        <span className="font-medium text-[var(--text-primary)]">
                          {exp.row_count > 0 ? formatNumber(exp.row_count) : "—"}
                        </span>
                        {exp.blocked_count > 0 && (
                          <span className="ml-1.5 text-[11px] text-amber-700">
                            (-{exp.blocked_count} bloccati)
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-3">
                        <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${badge.className}`}>
                          {badge.label}
                        </span>
                      </td>
                      <td className="px-3 py-3 tabular-nums text-[12px] text-[var(--text-muted)]">
                        {formatBytes(exp.size_bytes)}
                      </td>
                      <td className="px-3 py-3 whitespace-nowrap text-[11px] text-[var(--text-muted)]">
                        {formatDateIT(exp.created_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex items-center gap-1">
                          <button
                            type="button"
                            onClick={() => setPreviewId(exp.id)}
                            title="Anteprima e approvazione HITL"
                            className="flex h-7 items-center gap-1 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[11px] font-medium hover:bg-[var(--bg-subtle)]"
                          >
                            <Eye className="h-3 w-3" />
                            <span>Anteprima</span>
                          </button>
                          <a
                            href={api.getExportDownloadUrl(exp.id)}
                            title="Scarica file"
                            className="flex h-7 w-7 items-center justify-center rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] text-[#1D4ED8] hover:bg-[var(--accent-tint)]"
                          >
                            <Download className="h-3.5 w-3.5" />
                          </a>
                          {exp.origin === "generated" && (
                            <button
                              type="button"
                              onClick={() => handleDelete(exp.id)}
                              title="Elimina export"
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

      <ExportPreviewDrawer
        exportId={previewId}
        onClose={() => setPreviewId(null)}
        onUpdated={() => loadExports()}
      />

      <ExportModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        searchId={newSearchId}
        searchName={selectedSearchName}
        selectedIds={[]}
        activeFilterParams={{
          view: "all",
          q: "",
          product: "",
          tier: "",
          city: "",
          niche: "",
          lia_status: "",
          callable_only: false,
          has_email: false,
          has_valid_piva: false,
        }}
        estimatedCount={selectedSearchCount}
        onGenerated={() => loadExports()}
      />
    </div>
  );
}
