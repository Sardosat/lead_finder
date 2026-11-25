"use client";

import React, { useState } from "react";
import Link from "next/link";
import { CheckCircle2, Download, FileSpreadsheet, ShieldCheck, Webhook, X } from "lucide-react";
import { api } from "@/lib/api";
import type { ExportRecord } from "@/lib/types";

interface ExportModalProps {
  open: boolean;
  onClose: () => void;
  searchId: string;
  searchName: string;
  selectedIds: string[];
  activeFilterParams: {
    view: string;
    q: string;
    product: string;
    tier: string;
    city: string;
    niche: string;
    lia_status: string;
    callable_only: boolean;
    has_email: boolean;
    has_valid_piva: boolean;
  };
  estimatedCount: number;
  initialFormat?: "CSV" | "XLSX" | "WEBHOOK_JSON";
  onGenerated?: (rec: ExportRecord) => void;
}

export function ExportModal({
  open,
  onClose,
  searchId,
  searchName,
  selectedIds,
  activeFilterParams,
  estimatedCount,
  initialFormat = "CSV",
  onGenerated,
}: ExportModalProps) {
  const [format, setFormat] = useState<"CSV" | "XLSX" | "WEBHOOK_JSON">(initialFormat);
  const [prefix, setPrefix] = useState("export_lead");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<ExportRecord | null>(null);

  React.useEffect(() => {
    if (open) {
      setFormat(initialFormat);
      setCreated(null);
      setError("");
    }
  }, [open, initialFormat]);

  if (!open) return null;

  const handleGenerate = async () => {
    setLoading(true);
    setError("");
    try {
      const rec = await api.generateExport({
        search_id: searchId,
        format,
        lead_ids: selectedIds.length > 0 ? selectedIds : undefined,
        ...(selectedIds.length === 0 ? activeFilterParams : {}),
        filename_prefix: prefix.trim() || "export_lead",
      });
      setCreated(rec);
      onGenerated?.(rec);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore generazione export.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="fixed inset-0 bg-slate-900/35" onClick={onClose} />
      <div className="relative z-10 w-full max-w-md surface-panel p-5 shadow-xl">
        <div className="flex items-center justify-between border-b border-[var(--border-hairline)] pb-3 mb-4">
          <div>
            <h2 className="text-[14px] font-semibold text-[var(--text-primary)]">
              Salva Export in Archivio
            </h2>
            <p className="text-[12px] text-[var(--text-muted)]">{searchName}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-[var(--text-muted)] hover:bg-[var(--bg-subtle)]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {created ? (
          <div className="space-y-4">
            <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3.5 text-[12px] text-emerald-900">
              <div className="flex items-center gap-2 font-semibold">
                <CheckCircle2 className="h-4 w-4 text-emerald-700" />
                <span>Export salvato in Archivio Export</span>
              </div>
              <div className="mt-1.5 font-mono text-[11px]">{created.filename}</div>
              <div className="mt-1">
                Righe esportate: <strong>{created.row_count}</strong> · Escluse da GDPR/Blacklist:{" "}
                <strong>{created.blocked_count}</strong>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2">
              <Link
                href="/exports"
                onClick={onClose}
                className="h-8 flex items-center rounded-md border border-[var(--border-hairline)] px-3 text-[12px] font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
              >
                Vai ad Archivio Export
              </Link>
              <a
                href={api.getExportDownloadUrl(created.id)}
                className="h-8 flex items-center gap-1.5 rounded-md bg-[#1D4ED8] px-3 text-[12px] font-medium text-white hover:bg-[#1E40AF]"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Scarica File</span>
              </a>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="surface-subtle px-3 py-2 text-[12px] text-[var(--text-secondary)]">
              Ambito:{" "}
              <strong>
                {selectedIds.length > 0
                  ? `${selectedIds.length} lead selezionati manualmente`
                  : `Vista filtrata (${estimatedCount} lead candidati)`}
              </strong>
            </div>

            <div>
              <label className="block text-[12px] font-medium text-[var(--text-primary)] mb-1.5">
                Formato File
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { key: "CSV", label: "CSV UTF-8", icon: Download },
                  { key: "XLSX", label: "Excel (.xlsx)", icon: FileSpreadsheet },
                  { key: "WEBHOOK_JSON", label: "Webhook JSON", icon: Webhook },
                ].map((opt) => {
                  const Icon = opt.icon;
                  const active = format === opt.key;
                  return (
                    <button
                      key={opt.key}
                      type="button"
                      onClick={() => setFormat(opt.key as "CSV" | "XLSX" | "WEBHOOK_JSON")}
                      className={`flex flex-col items-center gap-1 rounded-md border p-2.5 text-[12px] font-medium transition-colors ${
                        active
                          ? "border-[#1D4ED8] bg-[var(--accent-tint)] text-[#1D4ED8]"
                          : "border-[var(--border-hairline)] bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      <span>{opt.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="block text-[12px] font-medium text-[var(--text-primary)] mb-1">
                Prefisso Nome File
              </label>
              <input
                type="text"
                value={prefix}
                onChange={(e) => setPrefix(e.target.value)}
                className="w-full h-9 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[13px] text-[var(--text-primary)] focus:border-[#1D4ED8] focus:outline-none"
              />
            </div>

            <div className="flex items-start gap-2 rounded-md border border-blue-200 bg-blue-50/70 p-2.5 text-[11px] text-blue-900">
              <ShieldCheck className="h-4 w-4 shrink-0 text-[#1D4ED8] mt-0.5" />
              <span>
                Conformità attiva: esclude automaticamente righe <code className="font-mono">BLOCKED</code>/Blacklist,
                non inserisce mai PEC nel campo email e salva i Webhook in stato <strong>Bozza HITL</strong>.
              </span>
            </div>

            {error && (
              <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
                {error}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={onClose}
                className="h-8 rounded-md border border-[var(--border-hairline)] px-3 text-[12px] font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]"
              >
                Annulla
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={handleGenerate}
                className="h-8 rounded-md bg-[#1D4ED8] px-3.5 text-[12px] font-medium text-white hover:bg-[#1E40AF] disabled:opacity-60"
              >
                {loading ? "Generazione..." : "Genera e Salva in Archivio"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
