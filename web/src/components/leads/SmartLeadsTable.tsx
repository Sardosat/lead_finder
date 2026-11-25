"use client";

import React, { useMemo, useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type VisibilityState,
} from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, Check, Copy, ExternalLink } from "lucide-react";
import { LIA_BADGE, PRODUCT_BADGE, TIER_BADGE } from "@/lib/formatters";
import type { LeadItem } from "@/lib/types";

interface SmartLeadsTableProps {
  items: LeadItem[];
  loading: boolean;
  density: "compact" | "standard";
  columnVisibility: VisibilityState;
  onColumnVisibilityChange: React.Dispatch<React.SetStateAction<VisibilityState>>;
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  onToggleSelectAllVisible: () => void;
  onInspectLead: (lead: LeadItem) => void;
  activeLeadId?: string;
  sortBy: string;
  sortDir: "asc" | "desc";
  onSortChange: (colKey: string) => void;
}

export function SmartLeadsTable({
  items,
  loading,
  density,
  columnVisibility,
  onColumnVisibilityChange,
  selectedIds,
  onToggleSelect,
  onToggleSelectAllVisible,
  onInspectLead,
  activeLeadId,
  sortBy,
  sortDir,
  onSortChange,
}: SmartLeadsTableProps) {
  const [copiedPhoneId, setCopiedPhoneId] = useState("");
  const allVisibleSelected = items.length > 0 && items.every((it) => selectedIds.includes(it.id));

  const copyPhone = async (e: React.MouseEvent, id: string, phone: string) => {
    e.stopPropagation();
    if (!phone) return;
    try {
      await navigator.clipboard.writeText(phone);
      setCopiedPhoneId(id);
      setTimeout(() => setCopiedPhoneId(""), 1400);
    } catch {
      // ignore
    }
  };

  const renderSortHeader = (label: string, key: string) => (
    <button
      type="button"
      onClick={() => onSortChange(key)}
      className="inline-flex items-center gap-1 font-semibold text-[11px] uppercase tracking-wide text-[var(--text-muted)] hover:text-[var(--text-primary)]"
    >
      <span>{label}</span>
      {sortBy === key ? (
        sortDir === "asc" ? (
          <ArrowUp className="h-3 w-3 text-[#1D4ED8]" />
        ) : (
          <ArrowDown className="h-3 w-3 text-[#1D4ED8]" />
        )
      ) : (
        <ArrowUpDown className="h-3 w-3 opacity-40" />
      )}
    </button>
  );

  const columns = useMemo<ColumnDef<LeadItem>[]>(
    () => [
      {
        id: "select",
        header: () => (
          <input
            type="checkbox"
            aria-label="Seleziona tutti visibili"
            checked={allVisibleSelected}
            onChange={onToggleSelectAllVisible}
            className="h-3.5 w-3.5 rounded border-[var(--border-strong)] accent-[#1D4ED8]"
          />
        ),
        cell: ({ row }) => (
          <div onClick={(e) => e.stopPropagation()}>
            <input
              type="checkbox"
              aria-label={`Seleziona ${row.original.company_name}`}
              checked={selectedIds.includes(row.original.id)}
              onChange={() => onToggleSelect(row.original.id)}
              className="h-3.5 w-3.5 rounded border-[var(--border-strong)] accent-[#1D4ED8]"
            />
          </div>
        ),
      },
      {
        id: "company_name",
        accessorKey: "company_name",
        header: () => renderSortHeader("Azienda", "company_name"),
        cell: ({ row }) => {
          const ld = row.original;
          return (
            <div className="min-w-[200px] max-w-[270px]">
              <div className="truncate font-medium text-[13px] text-[var(--text-primary)]">
                {ld.company_name}
              </div>
              <div className="truncate text-[11px] text-[var(--text-muted)]">{ld.niche || ld.category || "PMI"}</div>
            </div>
          );
        },
      },
      {
        id: "city",
        accessorKey: "city",
        header: () => renderSortHeader("Comune", "city"),
        cell: ({ row }) => (
          <div className="whitespace-nowrap">
            <div className="text-[12px] text-[var(--text-primary)]">{row.original.city || "—"}</div>
            {row.original.area_geografica && (
              <div className="text-[11px] text-[var(--text-muted)]">{row.original.area_geografica}</div>
            )}
          </div>
        ),
      },
      {
        id: "phone_e164",
        accessorKey: "phone_e164",
        header: () => renderSortHeader("Telefono E.164", "phone_e164"),
        cell: ({ row }) => {
          const ld = row.original;
          if (!ld.phone_e164) {
            return <span className="text-[11px] text-[var(--text-muted)]">Da arricchire</span>;
          }
          return (
            <div className="flex items-center gap-1.5 whitespace-nowrap">
              <span className="font-mono text-[12px] text-[var(--text-primary)]">{ld.phone_e164}</span>
              <button
                type="button"
                title="Copia numero"
                onClick={(e) => copyPhone(e, ld.id, ld.phone_e164)}
                className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"
              >
                {copiedPhoneId === ld.id ? (
                  <Check className="h-3 w-3 text-emerald-600" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </button>
            </div>
          );
        },
      },
      {
        id: "vat_id",
        accessorKey: "vat_id",
        header: () => renderSortHeader("P.IVA", "vat_id"),
        cell: ({ row }) => (
          <div className="flex items-center gap-1.5 whitespace-nowrap">
            <span className="font-mono text-[12px] text-[var(--text-secondary)]">
              {row.original.vat_id || "—"}
            </span>
            {row.original.has_valid_piva && (
              <span className="rounded bg-emerald-50 px-1 py-0.5 text-[10px] font-medium text-emerald-700">
                OK
              </span>
            )}
          </div>
        ),
      },
      {
        id: "email",
        accessorKey: "email",
        header: () => <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">Email / Web</span>,
        cell: ({ row }) => {
          const ld = row.original;
          return (
            <div className="max-w-[185px]">
              <div className="truncate font-mono text-[11px] text-[var(--text-secondary)]">
                {ld.email || (ld.pec ? "Solo PEC (isolata)" : "—")}
              </div>
              {ld.website && (
                <a
                  href={ld.website}
                  target="_blank"
                  rel="noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="inline-flex items-center gap-1 text-[11px] text-[#1D4ED8] hover:underline truncate max-w-[175px]"
                >
                  <span className="truncate">{ld.website.replace(/^https?:\/\//, "")}</span>
                  <ExternalLink className="h-2.5 w-2.5 shrink-0" />
                </a>
              )}
            </div>
          );
        },
      },
      {
        id: "brands",
        accessorKey: "brands",
        header: () => <span className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)]">Marchi Reali</span>,
        cell: ({ row }) => {
          const brands = row.original.brands || [];
          if (brands.length === 0) {
            return <span className="text-[11px] text-[var(--text-muted)]">—</span>;
          }
          return (
            <div className="max-w-[170px] truncate text-[12px] text-[var(--text-secondary)]" title={brands.join(", ")}>
              {brands.slice(0, 3).join(", ")}
              {brands.length > 3 ? ` +${brands.length - 3}` : ""}
            </div>
          );
        },
      },
      {
        id: "recommended_product",
        accessorKey: "recommended_product",
        header: () => renderSortHeader("Prodotto", "recommended_product"),
        cell: ({ row }) => {
          const badge = PRODUCT_BADGE[row.original.recommended_product] || PRODUCT_BADGE.rsksystem;
          return (
            <span className={`inline-block rounded border px-1.5 py-0.5 text-[11px] font-medium whitespace-nowrap ${badge.className}`}>
              {badge.label}
            </span>
          );
        },
      },
      {
        id: "icp_score",
        accessorKey: "icp_score",
        header: () => renderSortHeader("ICP / Tier", "icp_score"),
        cell: ({ row }) => {
          const ld = row.original;
          const tb = TIER_BADGE[ld.tier_code] || TIER_BADGE.C;
          return (
            <div className="flex items-center gap-2 whitespace-nowrap tabular-nums">
              <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${tb.className}`}>
                {tb.label}
              </span>
              <div className="flex items-center gap-1.5">
                <div className="h-1.5 w-11 rounded-full bg-[var(--bg-subtle)] overflow-hidden">
                  <div
                    className={`h-full ${
                      ld.icp_score >= 70 ? "bg-emerald-600" : ld.icp_score >= 40 ? "bg-amber-500" : "bg-slate-400"
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, ld.icp_score))}%` }}
                  />
                </div>
                <span className="text-[12px] font-medium text-[var(--text-primary)]">{ld.icp_score}</span>
              </div>
            </div>
          );
        },
      },
      {
        id: "lia_status",
        accessorKey: "lia_status",
        header: () => renderSortHeader("GDPR LIA", "lia_status"),
        cell: ({ row }) => {
          const lb = LIA_BADGE[row.original.lia_status] || LIA_BADGE.REVIEW_REQUIRED;
          return (
            <span className={`inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 text-[10px] font-medium whitespace-nowrap ${lb.className}`}>
              <span className={`h-1.5 w-1.5 rounded-full ${lb.dot}`} />
              <span>{lb.label}</span>
            </span>
          );
        },
      },
    ],
    [allVisibleSelected, onToggleSelectAllVisible, selectedIds, onToggleSelect, sortBy, sortDir, onSortChange, copiedPhoneId]
  );

  const table = useReactTable({
    data: items,
    columns,
    state: { columnVisibility },
    onColumnVisibilityChange,
    getCoreRowModel: getCoreRowModel(),
  });

  const cellPad = density === "compact" ? "px-3 py-2" : "px-3.5 py-3";

  return (
    <div className="surface-panel overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left">
          <thead className="border-b border-[var(--border-hairline)] bg-[var(--bg-subtle)]">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th key={header.id} className="px-3 py-2.5 whitespace-nowrap">
                    {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-[var(--border-hairline)]">
            {loading ? (
              Array.from({ length: 8 }).map((_, idx) => (
                <tr key={idx}>
                  <td colSpan={table.getVisibleLeafColumns().length} className="px-4 py-3">
                    <div className="h-4 w-full animate-pulse rounded bg-[var(--bg-subtle)]" />
                  </td>
                </tr>
              ))
            ) : items.length === 0 ? (
              <tr>
                <td
                  colSpan={table.getVisibleLeafColumns().length}
                  className="px-4 py-12 text-center text-[13px] text-[var(--text-muted)]"
                >
                  Nessuna azienda trovata con i filtri attuali. Prova ad allargare i criteri di ricerca.
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => {
                const isSelected = selectedIds.includes(row.original.id);
                const isInspected = activeLeadId === row.original.id;
                return (
                  <tr
                    key={row.id}
                    onClick={() => onInspectLead(row.original)}
                    className={`cursor-pointer transition-colors ${
                      isInspected
                        ? "bg-[var(--accent-tint)]"
                        : isSelected
                          ? "bg-blue-50/50 dark:bg-blue-950/20"
                          : "hover:bg-[var(--bg-subtle)]"
                    }`}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className={cellPad}>
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
