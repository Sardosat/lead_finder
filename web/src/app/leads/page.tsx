"use client";

import React, { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { VisibilityState } from "@tanstack/react-table";
import {
  Ban,
  ChevronLeft,
  ChevronRight,
  Columns3,
  Download,
  FileSpreadsheet,
  RotateCcw,
  Search,
  Webhook,
} from "lucide-react";
import { ExportModal } from "@/components/exports/ExportModal";
import { LeadInspectorDrawer } from "@/components/leads/LeadInspectorDrawer";
import { SmartLeadsTable } from "@/components/leads/SmartLeadsTable";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/formatters";
import type { LeadFacetsResponse, LeadItem, LeadsResponse, SavedSearch } from "@/lib/types";

const QUICK_VIEWS = [
  { id: "all", label: "Tutti" },
  { id: "callable_ab", label: "Chiamabili Tier A+B" },
  { id: "to_enrich", label: "Da Arricchire (No Tel)" },
  { id: "tecnicolive", label: "TecnicoLIVE" },
  { id: "rsksystem", label: "RSK System" },
  { id: "monetizelab", label: "MonetizeLab" },
];

const COLUMN_LABELS: Record<string, string> = {
  city: "Comune",
  phone_e164: "Telefono E.164",
  vat_id: "Partita IVA",
  email: "Email / Web",
  brands: "Marchi Reali",
  recommended_product: "Prodotto",
  icp_score: "ICP / Tier",
  lia_status: "GDPR LIA",
};

function LeadFinderContent() {
  const searchParams = useSearchParams();
  const initialSearchId = searchParams.get("search_id") || "ds-outbound-tecnicolive";
  const initialView = searchParams.get("view") || "all";

  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [searchId, setSearchId] = useState(initialSearchId);
  const [view, setView] = useState(initialView);
  const [qInput, setQInput] = useState("");
  const [q, setQ] = useState("");
  const [city, setCity] = useState("");
  const [niche, setNiche] = useState("");
  const [tier, setTier] = useState("");
  const [liaStatus, setLiaStatus] = useState("");
  const [callableOnly, setCallableOnly] = useState(false);
  const [hasValidPiva, setHasValidPiva] = useState(false);
  const [hasEmail, setHasEmail] = useState(false);
  const [sortBy, setSortBy] = useState("icp_score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  const [density, setDensity] = useState<"compact" | "standard">("compact");
  const [colMenuOpen, setColMenuOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  const [data, setData] = useState<LeadsResponse | null>(null);
  const [facets, setFacets] = useState<LeadFacetsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [inspectedLead, setInspectedLead] = useState<LeadItem | null>(null);

  const [exportOpen, setExportOpen] = useState(false);
  const [exportFmt, setExportFmt] = useState<"CSV" | "XLSX" | "WEBHOOK_JSON">("CSV");

  // Sync query string param changes
  useEffect(() => {
    const qsId = searchParams.get("search_id");
    if (qsId) setSearchId(qsId);
  }, [searchParams]);

  // Debounce text search
  useEffect(() => {
    const t = setTimeout(() => {
      setQ(qInput);
      setPage(1);
    }, 250);
    return () => clearTimeout(t);
  }, [qInput]);

  useEffect(() => {
    api
      .getSearches()
      .then((res) => setSearches(res.searches.filter((s) => s.leads_count > 0)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    api
      .getLeadFacets(searchId)
      .then(setFacets)
      .catch(() => setFacets(null));
  }, [searchId]);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.getLeads({
        search_id: searchId,
        view,
        q,
        tier,
        city,
        niche,
        lia_status: liaStatus,
        callable_only: callableOnly,
        has_email: hasEmail,
        has_valid_piva: hasValidPiva,
        sort_by: sortBy,
        sort_dir: sortDir,
        page,
        page_size: pageSize,
      });
      setData(res);
    } finally {
      setLoading(false);
    }
  }, [searchId, view, q, tier, city, niche, liaStatus, callableOnly, hasEmail, hasValidPiva, sortBy, sortDir, page, pageSize]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  const handleResetFilters = () => {
    setView("all");
    setQInput("");
    setQ("");
    setCity("");
    setNiche("");
    setTier("");
    setLiaStatus("");
    setCallableOnly(false);
    setHasValidPiva(false);
    setHasEmail(false);
    setPage(1);
  };

  const handleSortChange = (colKey: string) => {
    if (sortBy === colKey) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(colKey);
      setSortDir("desc");
    }
    setPage(1);
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const toggleSelectAllVisible = () => {
    const items = data?.items || [];
    const allIn = items.length > 0 && items.every((i) => selectedIds.includes(i.id));
    if (allIn) {
      const visibleSet = new Set(items.map((i) => i.id));
      setSelectedIds((prev) => prev.filter((id) => !visibleSet.has(id)));
    } else {
      setSelectedIds((prev) => Array.from(new Set([...prev, ...items.map((i) => i.id)])));
    }
  };

  const handleBulkBlacklist = async () => {
    const items = (data?.items || []).filter((i) => selectedIds.includes(i.id));
    for (const item of items) {
      await api.addSuppression({
        phone_e164: item.phone_e164,
        email: item.email,
        vat_id: item.vat_id,
        reason: "CANCELLAMI (Azione Batch Lead Finder)",
      });
    }
    setSelectedIds([]);
    fetchLeads();
  };

  const activeSearchName = searches.find((s) => s.id === searchId)?.name || searchId;
  const items = data?.items || [];
  const inspectedIdx = inspectedLead ? items.findIndex((i) => i.id === inspectedLead.id) : -1;

  return (
    <div className="space-y-4 max-w-[1440px] pb-16">
      {/* Top Dataset Selector + Export Trigger */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2.5">
          <select
            value={searchId}
            onChange={(e) => {
              setSearchId(e.target.value);
              setSelectedIds([]);
              setPage(1);
            }}
            className="h-9 max-w-full min-w-0 w-full sm:w-auto rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[13px] font-medium text-[var(--text-primary)] focus:border-[#1D4ED8] focus:outline-none"
          >
            {searches.length === 0 ? (
              <option value="ds-outbound-tecnicolive">Campagna Outbound Chiamabili (E.164)</option>
            ) : (
              searches.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({formatNumber(s.leads_count)})
                </option>
              ))
            )}
          </select>

          {data && (
            <div className="flex items-center gap-3 text-[12px] text-[var(--text-muted)] tabular-nums">
              <span>
                <strong className="text-[var(--text-primary)]">{formatNumber(data.total)}</strong> risultati
              </span>
              <span>·</span>
              <span>{formatNumber(data.summary.filtered_callable)} chiamabili E.164</span>
              <span>·</span>
              <span>{formatNumber(data.summary.filtered_valid_piva)} P.IVA valide</span>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={() => {
            setExportFmt("CSV");
            setExportOpen(true);
          }}
          className="flex h-9 items-center gap-1.5 rounded-md bg-[#1D4ED8] px-3.5 text-[12px] font-medium text-white hover:bg-[#1E40AF] transition-colors"
        >
          <Download className="h-3.5 w-3.5" />
          <span>Salva Export in Archivio</span>
        </button>
      </div>

      {/* Quick Views + Faceted Filter Toolbar */}
      <div className="surface-panel p-3 space-y-3">
        {/* Quick View Tabs */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-hairline)] pb-2.5">
          <div className="flex flex-wrap items-center gap-1">
            {QUICK_VIEWS.map((qv) => (
              <button
                key={qv.id}
                type="button"
                onClick={() => {
                  setView(qv.id);
                  setPage(1);
                }}
                className={`rounded-md px-2.5 py-1 text-[12px] font-medium transition-colors ${
                  view === qv.id
                    ? "bg-[var(--accent-tint)] text-[#1D4ED8]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
                }`}
              >
                {qv.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            {/* Density toggle */}
            <div className="inline-flex rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-0.5 text-[11px]">
              <button
                type="button"
                onClick={() => setDensity("compact")}
                className={`rounded px-2 py-0.5 ${density === "compact" ? "bg-[var(--bg-surface)] font-medium text-[var(--text-primary)]" : "text-[var(--text-muted)]"}`}
              >
                Compatta
              </button>
              <button
                type="button"
                onClick={() => setDensity("standard")}
                className={`rounded px-2 py-0.5 ${density === "standard" ? "bg-[var(--bg-surface)] font-medium text-[var(--text-primary)]" : "text-[var(--text-muted)]"}`}
              >
                Standard
              </button>
            </div>

            {/* Column Visibility Popover */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setColMenuOpen((v) => !v)}
                className="flex h-7 items-center gap-1.5 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[11px] font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]"
              >
                <Columns3 className="h-3.5 w-3.5" />
                <span>Colonne</span>
              </button>
              {colMenuOpen && (
                <div className="absolute right-0 mt-1 z-30 w-48 surface-panel p-2 shadow-lg space-y-1">
                  {Object.entries(COLUMN_LABELS).map(([colKey, label]) => {
                    const checked = columnVisibility[colKey] !== false;
                    return (
                      <label
                        key={colKey}
                        className="flex items-center gap-2 rounded px-2 py-1 text-[12px] hover:bg-[var(--bg-subtle)] cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={() =>
                            setColumnVisibility((prev) => ({
                              ...prev,
                              [colKey]: !checked,
                            }))
                          }
                          className="accent-[#1D4ED8]"
                        />
                        <span>{label}</span>
                      </label>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Filter Inputs Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-2">
          <div className="relative lg:col-span-2">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[var(--text-muted)]" />
            <input
              type="text"
              value={qInput}
              onChange={(e) => setQInput(e.target.value)}
              placeholder="Cerca azienda, P.IVA, telefono, marchi..."
              className="w-full h-8 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] pl-8 pr-2.5 text-[12px] text-[var(--text-primary)] focus:border-[#1D4ED8] focus:outline-none"
            />
          </div>

          <select
            value={city}
            onChange={(e) => {
              setCity(e.target.value);
              setPage(1);
            }}
            className="h-8 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px] text-[var(--text-primary)]"
          >
            <option value="">Tutti i Comuni</option>
            {(facets?.cities || []).map((c) => (
              <option key={c.value} value={c.value}>
                {c.value} ({c.count})
              </option>
            ))}
          </select>

          <select
            value={niche}
            onChange={(e) => {
              setNiche(e.target.value);
              setPage(1);
            }}
            className="h-8 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px] text-[var(--text-primary)]"
          >
            <option value="">Tutte le Nicchie</option>
            {(facets?.niches || []).map((n) => (
              <option key={n.value} value={n.value}>
                {n.value} ({n.count})
              </option>
            ))}
          </select>

          <select
            value={tier}
            onChange={(e) => {
              setTier(e.target.value);
              setPage(1);
            }}
            className="h-8 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px] text-[var(--text-primary)]"
          >
            <option value="">Tutti i Tier</option>
            <option value="A">Tier A (VIP Hot)</option>
            <option value="B">Tier B (Warm)</option>
            <option value="C">Tier C (Cold / Da arricchire)</option>
          </select>

          <select
            value={liaStatus}
            onChange={(e) => {
              setLiaStatus(e.target.value);
              setPage(1);
            }}
            className="h-8 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px] text-[var(--text-primary)]"
          >
            <option value="">Stato LIA (Tutti)</option>
            <option value="PASS">LIA PASS</option>
            <option value="REVIEW_REQUIRED">LIA Revisione</option>
            <option value="BLOCKED">LIA Bloccati</option>
          </select>
        </div>

        {/* Boolean toggles & Reset */}
        <div className="flex flex-wrap items-center justify-between gap-2 text-[12px]">
          <div className="flex flex-wrap items-center gap-3">
            <label className="inline-flex items-center gap-1.5 cursor-pointer text-[var(--text-secondary)]">
              <input
                type="checkbox"
                checked={callableOnly}
                onChange={(e) => {
                  setCallableOnly(e.target.checked);
                  setPage(1);
                }}
                className="accent-[#1D4ED8]"
              />
              <span>Solo chiamabili E.164</span>
            </label>
            <label className="inline-flex items-center gap-1.5 cursor-pointer text-[var(--text-secondary)]">
              <input
                type="checkbox"
                checked={hasValidPiva}
                onChange={(e) => {
                  setHasValidPiva(e.target.checked);
                  setPage(1);
                }}
                className="accent-[#1D4ED8]"
              />
              <span>Solo P.IVA valida</span>
            </label>
            <label className="inline-flex items-center gap-1.5 cursor-pointer text-[var(--text-secondary)]">
              <input
                type="checkbox"
                checked={hasEmail}
                onChange={(e) => {
                  setHasEmail(e.target.checked);
                  setPage(1);
                }}
                className="accent-[#1D4ED8]"
              />
              <span>Con email non-PEC</span>
            </label>
          </div>

          <button
            type="button"
            onClick={handleResetFilters}
            className="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            <RotateCcw className="h-3 w-3" />
            <span>Azzera filtri</span>
          </button>
        </div>
      </div>

      {/* Smart Data Grid */}
      <SmartLeadsTable
        items={items}
        loading={loading}
        density={density}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        selectedIds={selectedIds}
        onToggleSelect={toggleSelect}
        onToggleSelectAllVisible={toggleSelectAllVisible}
        onInspectLead={(ld) => setInspectedLead(ld)}
        activeLeadId={inspectedLead?.id}
        sortBy={sortBy}
        sortDir={sortDir}
        onSortChange={handleSortChange}
      />

      {/* Pagination Footer */}
      {data && (
        <div className="flex flex-wrap items-center justify-between gap-3 text-[12px] text-[var(--text-secondary)]">
          <div className="flex items-center gap-2">
            <span>Righe per pagina:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              className="h-7 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px]"
            >
              {[25, 50, 100].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 tabular-nums">
            <span>
              Pagina <strong>{data.page}</strong> di <strong>{data.total_pages}</strong>
            </span>
            <button
              type="button"
              disabled={data.page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="flex h-7 w-7 items-center justify-center rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] hover:bg-[var(--bg-subtle)] disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              disabled={data.page >= data.total_pages}
              onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
              className="flex h-7 w-7 items-center justify-center rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] hover:bg-[var(--bg-subtle)] disabled:opacity-40"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Floating Bulk Action Bar */}
      {selectedIds.length > 0 && (
        <div className="fixed bottom-5 left-1/2 -translate-x-1/2 z-30 flex flex-wrap items-center gap-2 rounded-lg border border-[var(--border-strong)] bg-[var(--bg-surface)] px-4 py-2.5 shadow-lg text-[12px]">
          <span className="font-semibold tabular-nums text-[var(--text-primary)] mr-1">
            {selectedIds.length} selezionati
          </span>
          <button
            type="button"
            onClick={() => {
              setExportFmt("CSV");
              setExportOpen(true);
            }}
            className="flex h-7 items-center gap-1 rounded border border-[var(--border-hairline)] px-2.5 font-medium hover:bg-[var(--bg-subtle)]"
          >
            <Download className="h-3.5 w-3.5" />
            <span>CSV</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setExportFmt("XLSX");
              setExportOpen(true);
            }}
            className="flex h-7 items-center gap-1 rounded border border-[var(--border-hairline)] px-2.5 font-medium hover:bg-[var(--bg-subtle)]"
          >
            <FileSpreadsheet className="h-3.5 w-3.5" />
            <span>Excel</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setExportFmt("WEBHOOK_JSON");
              setExportOpen(true);
            }}
            className="flex h-7 items-center gap-1 rounded border border-[var(--border-hairline)] px-2.5 font-medium hover:bg-[var(--bg-subtle)]"
          >
            <Webhook className="h-3.5 w-3.5" />
            <span>Bozza Webhook</span>
          </button>
          <button
            type="button"
            onClick={handleBulkBlacklist}
            className="flex h-7 items-center gap-1 rounded border border-red-200 bg-red-50 px-2.5 font-medium text-red-700 hover:bg-red-100"
          >
            <Ban className="h-3.5 w-3.5" />
            <span>Blacklist</span>
          </button>
          <button
            type="button"
            onClick={() => setSelectedIds([])}
            className="ml-1 text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            Annulla
          </button>
        </div>
      )}

      {/* Inspector Drawer */}
      <LeadInspectorDrawer
        lead={inspectedLead}
        onClose={() => setInspectedLead(null)}
        hasPrev={inspectedIdx > 0}
        hasNext={inspectedIdx >= 0 && inspectedIdx < items.length - 1}
        onPrev={() => inspectedIdx > 0 && setInspectedLead(items[inspectedIdx - 1])}
        onNext={() => inspectedIdx >= 0 && inspectedIdx < items.length - 1 && setInspectedLead(items[inspectedIdx + 1])}
        onBlacklisted={() => {
          setInspectedLead(null);
          fetchLeads();
        }}
      />

      {/* Export Modal */}
      <ExportModal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        searchId={searchId}
        searchName={activeSearchName}
        selectedIds={selectedIds}
        activeFilterParams={{
          view,
          q,
          product: "",
          tier,
          city,
          niche,
          lia_status: liaStatus,
          callable_only: callableOnly,
          has_email: hasEmail,
          has_valid_piva: hasValidPiva,
        }}
        estimatedCount={data?.total || 0}
        initialFormat={exportFmt}
      />
    </div>
  );
}

export default function LeadsPage() {
  return (
    <Suspense fallback={<div className="p-6 text-[13px] text-[var(--text-muted)]">Caricamento Lead Finder...</div>}>
      <LeadFinderContent />
    </Suspense>
  );
}
