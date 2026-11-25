"use client";

import React, { useEffect, useState } from "react";
import { CheckCircle2, Download, Send, ShieldCheck, X } from "lucide-react";
import { api } from "@/lib/api";
import { APPROVAL_BADGE, formatBytes, formatDateIT } from "@/lib/formatters";
import type { ExportRecord } from "@/lib/types";

interface ExportPreviewDrawerProps {
  exportId: string | null;
  onClose: () => void;
  onUpdated: (rec: ExportRecord) => void;
}

export function ExportPreviewDrawer({ exportId, onClose, onUpdated }: ExportPreviewDrawerProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<{
    format: string;
    columns?: string[];
    rows?: Array<Record<string, string>>;
    json_preview?: Record<string, unknown>;
    text_preview?: string;
    note?: string;
    record: ExportRecord;
  } | null>(null);

  const [humanConfirmed, setHumanConfirmed] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [actionMsg, setActionMsg] = useState("");

  useEffect(() => {
    if (!exportId) return;
    setLoading(true);
    setError("");
    setActionMsg("");
    setHumanConfirmed(false);
    api
      .previewExport(exportId)
      .then((res) => {
        setPreview(res);
        setWebhookUrl(res.record.webhook_url || "");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Errore anteprima export."))
      .finally(() => setLoading(false));
  }, [exportId]);

  if (!exportId) return null;

  const handleApprove = async (dispatchWebhook: boolean) => {
    if (!preview) return;
    setSubmitting(true);
    setError("");
    setActionMsg("");
    try {
      const res = await api.approveExport(preview.record.id, {
        human_approved: humanConfirmed,
        dispatch_webhook: dispatchWebhook,
        webhook_url: webhookUrl.trim() || undefined,
      });
      setPreview({ ...preview, record: res.record });
      onUpdated(res.record);
      setActionMsg(
        res.dispatched
          ? "Payload inviato al Webhook configurato."
          : "Export segnato come Approvato dopo revisione umana."
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore approvazione.");
    } finally {
      setSubmitting(false);
    }
  };

  const rec = preview?.record;
  const badge = rec ? APPROVAL_BADGE[rec.approval_status] || APPROVAL_BADGE.DRAFT : null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="fixed inset-0 bg-slate-900/30" onClick={onClose} />
      <aside className="relative z-10 flex h-full w-full max-w-[680px] flex-col bg-[var(--bg-surface)] border-l border-[var(--border-hairline)] shadow-xl">
        <div className="flex items-start justify-between gap-3 border-b border-[var(--border-hairline)] px-5 py-3.5">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-1.5 py-0.5 font-mono text-[10px] font-semibold">
                {rec?.format || "..."}
              </span>
              {badge && (
                <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${badge.className}`}>
                  {badge.label}
                </span>
              )}
            </div>
            <h2 className="mt-1 truncate text-[14px] font-semibold text-[var(--text-primary)]">
              {rec?.filename || "Anteprima Export"}
            </h2>
            {rec && (
              <div className="text-[11px] text-[var(--text-muted)]">
                {rec.search_name} · {rec.row_count} righe · {formatBytes(rec.size_bytes)} · {formatDateIT(rec.created_at)}
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {rec && (
              <a
                href={api.getExportDownloadUrl(rec.id)}
                className="flex h-7 items-center gap-1 rounded bg-[#1D4ED8] px-2.5 text-[12px] font-medium text-white hover:bg-[#1E40AF]"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Scarica</span>
              </a>
            )}
            <button
              type="button"
              onClick={onClose}
              className="flex h-7 w-7 items-center justify-center rounded border border-[var(--border-hairline)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {loading ? (
            <div className="text-[13px] text-[var(--text-muted)]">Caricamento anteprima...</div>
          ) : error && !preview ? (
            <div className="rounded-md border border-red-200 bg-red-50 p-3 text-[12px] text-red-700">
              {error}
            </div>
          ) : preview ? (
            <>
              {/* Human-in-the-Loop Gate for Webhook / Outbound Drafts */}
              {preview.format === "WEBHOOK_JSON" && (
                <div className="surface-subtle p-4 space-y-3">
                  <div className="flex items-center gap-1.5 text-[12px] font-semibold text-[var(--text-primary)]">
                    <ShieldCheck className="h-4 w-4 text-[#1D4ED8]" />
                    <span>Conferma Umana Obbligatoria (AGENTS.md §1)</span>
                  </div>
                  <label className="flex items-start gap-2 text-[12px] text-[var(--text-secondary)] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={humanConfirmed}
                      onChange={(e) => setHumanConfirmed(e.target.checked)}
                      className="mt-0.5 accent-[#1D4ED8]"
                    />
                    <span>
                      Confermo di aver revisionato i contatti e i testi GDPR nel payload e autorizzo l&apos;approvazione / consegna al CRM.
                    </span>
                  </label>
                  <div className="flex flex-wrap items-center gap-2">
                    <input
                      type="url"
                      value={webhookUrl}
                      onChange={(e) => setWebhookUrl(e.target.value)}
                      placeholder="https://... (opzionale per invio Webhook RSK/GHL/n8n)"
                      className="flex-1 min-w-[220px] h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px]"
                    />
                    <button
                      type="button"
                      disabled={!humanConfirmed || submitting}
                      onClick={() => handleApprove(false)}
                      className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[12px] font-medium hover:bg-[var(--bg-subtle)] disabled:opacity-40"
                    >
                      Approva Bozza
                    </button>
                    <button
                      type="button"
                      disabled={!humanConfirmed || submitting}
                      onClick={() => handleApprove(true)}
                      className="flex h-8 items-center gap-1.5 rounded bg-[#1D4ED8] px-3 text-[12px] font-medium text-white hover:bg-[#1E40AF] disabled:opacity-40"
                    >
                      <Send className="h-3 w-3" />
                      <span>Invia Webhook</span>
                    </button>
                  </div>
                  {actionMsg && (
                    <div className="flex items-center gap-1.5 text-[12px] font-medium text-emerald-700">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>{actionMsg}</span>
                    </div>
                  )}
                  {error && (
                    <div className="text-[12px] text-red-700">{error}</div>
                  )}
                </div>
              )}

              {/* Preview Table for CSV / XLSX */}
              {preview.rows && preview.columns && (
                <div className="surface-panel overflow-hidden">
                  <div className="border-b border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-2 text-[11px] font-medium text-[var(--text-muted)]">
                    Anteprima prime {preview.rows.length} righe ({preview.columns.length} colonne)
                  </div>
                  <div className="overflow-x-auto max-h-[55vh]">
                    <table className="w-full border-collapse text-left text-[11px]">
                      <thead className="border-b border-[var(--border-hairline)] bg-[var(--bg-subtle)]">
                        <tr>
                          {preview.columns.slice(0, 8).map((col) => (
                            <th key={col} className="px-2.5 py-2 font-semibold text-[var(--text-muted)] whitespace-nowrap">
                              {col}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border-hairline)]">
                        {preview.rows.map((r, i) => (
                          <tr key={i} className="hover:bg-[var(--bg-subtle)]">
                            {preview.columns!.slice(0, 8).map((col) => (
                              <td key={col} className="px-2.5 py-1.5 max-w-[180px] truncate text-[var(--text-primary)]">
                                {r[col] || "—"}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* JSON Preview */}
              {preview.json_preview && (
                <pre className="surface-subtle overflow-x-auto p-3.5 font-mono text-[11px] leading-relaxed text-[var(--text-primary)]">
                  {JSON.stringify(preview.json_preview, null, 2)}
                </pre>
              )}

              {/* Markdown Preview */}
              {preview.text_preview && (
                <pre className="surface-subtle whitespace-pre-wrap p-3.5 font-mono text-[12px] leading-relaxed text-[var(--text-primary)]">
                  {preview.text_preview}
                </pre>
              )}

              {/* PDF Note */}
              {preview.format === "PDF" && (
                <div className="surface-subtle p-4 text-[13px] text-[var(--text-secondary)]">
                  {preview.note} Usa il pulsante <strong>Scarica</strong> in alto a destra per aprire il documento PDF completo.
                </div>
              )}
            </>
          ) : null}
        </div>
      </aside>
    </div>
  );
}
