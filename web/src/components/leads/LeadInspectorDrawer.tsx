"use client";

import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  Ban,
  Building2,
  Check,
  CheckCircle2,
  Copy,
  ExternalLink,
  Flame,
  Globe,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Target,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { LIA_BADGE, PRODUCT_BADGE, TIER_BADGE } from "@/lib/formatters";
import type { LeadItem } from "@/lib/types";

interface LeadInspectorDrawerProps {
  lead: LeadItem | null;
  onClose: () => void;
  onPrev: () => void;
  onNext: () => void;
  hasPrev: boolean;
  hasNext: boolean;
  onBlacklisted: () => void;
}

type DrawerTab = "profile" | "swot" | "audit" | "ai" | "gdpr";

export function LeadInspectorDrawer({
  lead,
  onClose,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
  onBlacklisted,
}: LeadInspectorDrawerProps) {
  const [tab, setTab] = useState<DrawerTab>("profile");
  const [copiedKey, setCopiedKey] = useState("");
  const [viesLoading, setViesLoading] = useState(false);
  const [viesResult, setViesResult] = useState<Record<string, unknown> | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditResult, setAuditResult] = useState<Record<string, unknown> | null>(null);
  const [blacklisting, setBlacklisting] = useState(false);

  useEffect(() => {
    setViesResult(null);
    setAuditResult(null);
    setCopiedKey("");
  }, [lead?.id]);

  useEffect(() => {
    if (!lead) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowUp" && hasPrev) {
        e.preventDefault();
        onPrev();
      } else if (e.key === "ArrowDown" && hasNext) {
        e.preventDefault();
        onNext();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lead, hasPrev, hasNext, onClose, onPrev, onNext]);

  if (!lead) return null;

  const copyValue = async (key: string, value: string) => {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(""), 1600);
    } catch {
      // ignore clipboard errors
    }
  };

  const runViesCheck = async () => {
    if (!lead.vat_id) return;
    setViesLoading(true);
    try {
      const res = await api.checkVies(lead.vat_id, lead.country_code || "IT");
      setViesResult(res);
    } catch (err) {
      setViesResult({ status: "ERROR", message: err instanceof Error ? err.message : "Errore VIES" });
    } finally {
      setViesLoading(false);
    }
  };

  const runLiveTechAudit = async () => {
    if (!lead.website) return;
    setAuditLoading(true);
    try {
      const res = await api.runTechAudit(lead.website, true);
      setAuditResult(res);
    } catch (err) {
      setAuditResult({ error: err instanceof Error ? err.message : "Errore Audit" });
    } finally {
      setAuditLoading(false);
    }
  };

  const handleBlacklist = async () => {
    setBlacklisting(true);
    try {
      await api.addSuppression({
        phone_e164: lead.phone_e164,
        email: lead.email,
        vat_id: lead.vat_id,
        reason: "CANCELLAMI (Inspector Drawer)",
      });
      onBlacklisted();
    } finally {
      setBlacklisting(false);
    }
  };

  const prodBadge = PRODUCT_BADGE[lead.recommended_product] || PRODUCT_BADGE.rsksystem;
  const tierBadge = TIER_BADGE[lead.tier_code] || TIER_BADGE.C;
  const liaBadge = LIA_BADGE[lead.lia_status] || LIA_BADGE.REVIEW_REQUIRED;

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="fixed inset-0 bg-slate-900/25" onClick={onClose} />
      <aside className="relative z-10 flex h-full w-full max-w-[510px] flex-col bg-[var(--bg-surface)] border-l border-[var(--border-hairline)] shadow-xl">
        {/* Drawer Header */}
        <div className="border-b border-[var(--border-hairline)] px-5 py-3.5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5 mb-1">
                <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${tierBadge.className}`}>
                  {tierBadge.label} · {lead.icp_score}/100
                </span>
                <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${prodBadge.className}`}>
                  {prodBadge.label}
                </span>
                <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${liaBadge.className}`}>
                  LIA {liaBadge.label}
                </span>
              </div>
              <h2 className="truncate text-[15px] font-semibold text-[var(--text-primary)]">
                {lead.company_name}
              </h2>
              <p className="truncate text-[12px] text-[var(--text-muted)]">
                {lead.city || "N/D"} {lead.area_geografica ? `· ${lead.area_geografica}` : ""} · {lead.niche}
              </p>
            </div>

            <div className="flex items-center gap-1 shrink-0">
              <button
                type="button"
                disabled={!hasPrev}
                onClick={onPrev}
                title="Riga precedente (↑)"
                className="flex h-7 w-7 items-center justify-center rounded border border-[var(--border-hairline)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] disabled:opacity-35"
              >
                <ArrowUp className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                disabled={!hasNext}
                onClick={onNext}
                title="Riga successiva (↓)"
                className="flex h-7 w-7 items-center justify-center rounded border border-[var(--border-hairline)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] disabled:opacity-35"
              >
                <ArrowDown className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={onClose}
                title="Chiudi (Esc)"
                className="flex h-7 w-7 items-center justify-center rounded border border-[var(--border-hairline)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)]"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Drawer Tabs */}
          <div className="mt-3 flex gap-4 border-b border-[var(--border-hairline)] -mb-3.5 text-[12px]">
            {[
              { id: "profile", label: "Profilo & Fiscale" },
              { id: "swot", label: "Pain, Weak & Forza" },
              { id: "audit", label: "Audit L1 & Marchi" },
              { id: "ai", label: "AI & Pitch 1-to-1" },
              { id: "gdpr", label: "GDPR LIA" },
            ].map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTab(t.id as DrawerTab)}
                className={`pb-2.5 font-medium border-b-2 transition-colors ${
                  tab === t.id
                    ? "border-[#1D4ED8] text-[#1D4ED8]"
                    : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 text-[13px]">
          {tab === "profile" && (
            <>
              <div className="surface-subtle divide-y divide-[var(--border-hairline)] overflow-hidden">
                <div className="flex items-center justify-between px-3.5 py-2.5">
                  <span className="text-[12px] text-[var(--text-muted)]">Telefono Principale (E.164)</span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[12px] font-medium text-[var(--text-primary)]">
                      {lead.phone_e164 || "Non rilevato"}
                    </span>
                    {lead.phone_e164 && (
                      <button
                        type="button"
                        onClick={() => copyValue("phone", lead.phone_e164)}
                        className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"
                      >
                        {copiedKey === "phone" ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    )}
                  </div>
                </div>

                {lead.phone_secondary && (
                  <div className="flex items-center justify-between px-3.5 py-2.5">
                    <span className="text-[12px] text-[var(--text-muted)]">Altri Telefoni</span>
                    <span className="font-mono text-[12px] text-[var(--text-primary)]">{lead.phone_secondary}</span>
                  </div>
                )}

                <div className="flex items-center justify-between px-3.5 py-2.5">
                  <span className="text-[12px] text-[var(--text-muted)]">Email Outbound (Non-PEC)</span>
                  <span className="font-mono text-[12px] text-[var(--text-primary)]">
                    {lead.email || "Non disponibile"}
                  </span>
                </div>

                <div className="flex items-center justify-between px-3.5 py-2.5">
                  <span className="text-[12px] text-[var(--text-muted)]">PEC (Solo Registro — Bloccata)</span>
                  <span className="font-mono text-[12px] text-amber-700">
                    {lead.pec || "Nessuna PEC rilevata"}
                  </span>
                </div>

                <div className="flex items-center justify-between px-3.5 py-2.5">
                  <span className="text-[12px] text-[var(--text-muted)]">Sito Aziendale</span>
                  {lead.website ? (
                    <a
                      href={lead.website}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1 text-[12px] font-medium text-[#1D4ED8] hover:underline"
                    >
                      <Globe className="h-3.5 w-3.5" />
                      <span className="max-w-[240px] truncate">{lead.website}</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  ) : (
                    <span className="text-[12px] text-[var(--text-muted)]">Non rilevato</span>
                  )}
                </div>

                <div className="flex items-center justify-between px-3.5 py-2.5">
                  <span className="text-[12px] text-[var(--text-muted)]">Indirizzo</span>
                  <span className="text-right text-[12px] text-[var(--text-primary)] max-w-[270px]">
                    {lead.address || `${lead.city || "N/D"}`}
                  </span>
                </div>
              </div>

              {/* Fiscal & VIES Verification */}
              <div className="surface-panel p-3.5 space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
                      Dati Fiscali &amp; VIES UE
                    </div>
                    <div className="mt-0.5 flex items-center gap-2">
                      <span className="font-mono text-[13px] font-semibold text-[var(--text-primary)]">
                        {lead.vat_id || "P.IVA non rilevata"}
                      </span>
                      {lead.has_valid_piva && (
                        <span className="rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700">
                          Luhn OK
                        </span>
                      )}
                    </div>
                  </div>
                  {lead.vat_id && (
                    <button
                      type="button"
                      disabled={viesLoading}
                      onClick={runViesCheck}
                      className="h-7 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px] font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)] disabled:opacity-50"
                    >
                      {viesLoading ? "Verifica…" : "Verifica VIES Live"}
                    </button>
                  )}
                </div>

                {lead.cna_status && (
                  <div className="text-[12px] text-[var(--text-secondary)]">
                    <span className="font-medium">Stato CNA:</span> {lead.cna_status}
                  </div>
                )}

                {viesResult && (
                  <div className="rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-2.5 text-[12px] space-y-1">
                    <div className="font-semibold">
                      Esito VIES:{" "}
                      {viesResult.is_valid === true
                        ? "ATTIVA IN UE"
                        : viesResult.is_valid === false
                          ? "NON ATTIVA"
                          : String(viesResult.status || "N/D")}
                    </div>
                    {Boolean(viesResult.name) && <div>Ragione Ufficiale: {String(viesResult.name)}</div>}
                    {Boolean(viesResult.address) && <div>Sede Legale: {String(viesResult.address)}</div>}
                  </div>
                )}
              </div>
            </>
          )}

          {tab === "swot" && (
            <div className="space-y-4">
              {lead.sales_brief && (
                <div className="rounded-lg border border-blue-200 bg-blue-50/80 p-3.5 space-y-2">
                  <div className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-blue-800">
                    <Target className="h-3.5 w-3.5 text-blue-700" />
                    <span>Cosa Vendere e Perché (Pre-Call) · {lead.sales_brief.product_name}</span>
                  </div>
                  <div className="text-[13px] font-semibold text-slate-900">
                    {lead.sales_brief.recommended_plan}
                  </div>
                  <div className="flex flex-wrap gap-2 text-[11px] text-slate-700">
                    <span className="inline-flex items-center gap-1 rounded bg-white/80 px-2 py-0.5 border border-blue-100">
                      <Building2 className="h-3 w-3 text-blue-600" />
                      {lead.sales_brief.company_size_label}
                    </span>
                    <span className="rounded bg-white/80 px-2 py-0.5 border border-blue-100">
                      Tech: {lead.sales_brief.tech_maturity_label}
                    </span>
                  </div>
                  <p className="text-[12px] text-slate-700 leading-relaxed">{lead.sales_brief.why_sell}</p>
                  {lead.sales_brief.expected_objection && (
                    <div className="rounded border border-blue-200 bg-white/70 p-2 text-[11px] text-slate-700">
                      <strong>Obiezione attesa:</strong> {lead.sales_brief.expected_objection}
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-[12px] font-semibold text-red-800">
                  <Flame className="h-4 w-4 text-red-600" />
                  <span>Pain Points da Attaccare ({(lead.pain_signals || []).length})</span>
                </div>
                {(lead.pain_signals || []).map((p) => (
                  <div key={p.id} className="rounded-md border border-red-200 border-l-4 border-l-red-600 bg-red-50/70 p-2.5 space-y-1">
                    <div className="text-[12px] font-semibold text-red-900">{p.title}</div>
                    <div className="text-[11px] text-slate-700">{p.description}</div>
                    {p.attack_angle && (
                      <div className="text-[11px] font-medium text-red-800">Attacco: {p.attack_angle}</div>
                    )}
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-[12px] font-semibold text-amber-800">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  <span>Weak Points ({(lead.weak_points || []).length})</span>
                </div>
                {(lead.weak_points || []).map((w) => (
                  <div key={w.id} className="rounded-md border border-amber-200 border-l-4 border-l-amber-500 bg-amber-50/70 p-2.5 space-y-1">
                    <div className="text-[12px] font-semibold text-amber-900">{w.title}</div>
                    <div className="text-[11px] text-slate-700">{w.description}</div>
                    {w.evidence && <div className="text-[10px] text-amber-800">{w.evidence}</div>}
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-1.5 text-[12px] font-semibold text-emerald-800">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  <span>Strengths — Punti di Forza ({(lead.strengths || []).length})</span>
                </div>
                {(lead.strengths || []).map((s) => (
                  <div key={s.id} className="rounded-md border border-emerald-200 border-l-4 border-l-emerald-600 bg-emerald-50/70 p-2.5 space-y-1">
                    <div className="text-[12px] font-semibold text-emerald-900">{s.title}</div>
                    <div className="text-[11px] text-slate-700">{s.description}</div>
                    {s.evidence && <div className="text-[10px] text-emerald-800">{s.evidence}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === "audit" && (
            <>
              <div className="surface-panel p-3.5 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[12px] font-semibold text-[var(--text-primary)]">
                      Segnali Tecnici Reali (Zero Hallucination)
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)]">
                      Solo marchi e certificazioni effettivamente rilevati nei testi aziendali
                    </div>
                  </div>
                  {lead.website && (
                    <button
                      type="button"
                      disabled={auditLoading}
                      onClick={runLiveTechAudit}
                      className="h-7 rounded border border-[var(--border-hairline)] bg-[#1D4ED8] px-2.5 text-[12px] font-medium text-white hover:bg-[#1E40AF] disabled:opacity-50"
                    >
                      {auditLoading ? "Scansione…" : "Esegui Tech Audit L1"}
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-2.5 text-[12px]">
                  <div className="surface-subtle p-2.5">
                    <div className="text-[11px] text-[var(--text-muted)]">Marchi Verificati</div>
                    <div className="mt-1 font-medium text-[var(--text-primary)]">
                      {lead.brands.length > 0 ? lead.brands.join(", ") : "Nessun marchio rilevato"}
                    </div>
                  </div>
                  <div className="surface-subtle p-2.5">
                    <div className="text-[11px] text-[var(--text-muted)]">Certificazioni &amp; H24</div>
                    <div className="mt-1 font-medium text-[var(--text-primary)]">
                      {lead.certifications.length > 0 ? lead.certifications.join(", ") : "Standard"} ·{" "}
                      {lead.is_h24 ? "H24 Attivo" : "Orario Ufficio"}
                    </div>
                  </div>
                </div>

                {auditResult && (
                  <div className="surface-subtle p-3 space-y-1.5 text-[12px]">
                    <div className="font-semibold text-[var(--text-primary)]">
                      Risultato Scansione Live L1
                    </div>
                    <div>HTTP: {String(auditResult.http_status ?? "—")} · SSL: {auditResult.has_ssl ? "Sì" : "No"} · CMS: {String(auditResult.cms_stack ?? "Unknown")}</div>
                    <div>WhatsApp CTA: {auditResult.has_whatsapp_cta ? "Presente" : "Assente"} · Form Preventivo: {auditResult.has_booking_or_quote_form ? "Presente" : "Assente"}</div>
                    <div>Record MX Email: {auditResult.email_mx_valid === true ? "Valido" : auditResult.email_mx_valid === false ? "Non valido" : "Non verificato"}</div>
                    {Array.isArray(auditResult.tracking_pixels) && auditResult.tracking_pixels.length > 0 && (
                      <div>Pixel: {auditResult.tracking_pixels.join(", ")}</div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}

          {tab === "ai" && (
            <>
              <div className="surface-panel p-3.5 space-y-2">
                <div className="flex items-center gap-1.5 text-[12px] font-semibold text-[var(--text-primary)]">
                  <Sparkles className="h-3.5 w-3.5 text-[#1D4ED8]" />
                  <span>Routing Ecosistema: {lead.recommended_product_name}</span>
                </div>
                <p className="text-[12px] text-[var(--text-secondary)]">{lead.routing_rationale}</p>
                {lead.trigger_signal && (
                  <div className="text-[12px] text-[var(--text-primary)]">
                    <span className="font-medium">Trigger operativo:</span> {lead.trigger_signal}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] font-semibold text-[var(--text-primary)]">
                    Icebreaker 1-to-1 (Chiamata / Apertura)
                  </span>
                  <button
                    type="button"
                    onClick={() => copyValue("icebreaker", lead.icebreaker_1to1)}
                    className="flex items-center gap-1 text-[11px] font-medium text-[#1D4ED8] hover:underline"
                  >
                    {copiedKey === "icebreaker" ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    <span>{copiedKey === "icebreaker" ? "Copiato" : "Copia"}</span>
                  </button>
                </div>
                <div className="surface-subtle p-3 text-[12px] leading-relaxed text-[var(--text-primary)]">
                  {lead.icebreaker_1to1}
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[12px] font-semibold text-[var(--text-primary)]">
                    Bozza WhatsApp / Email (Mittente + Opt-Out GDPR inclusi)
                  </span>
                  <button
                    type="button"
                    onClick={() => copyValue("whatsapp", lead.whatsapp_draft)}
                    className="flex items-center gap-1 text-[11px] font-medium text-[#1D4ED8] hover:underline"
                  >
                    {copiedKey === "whatsapp" ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    <span>{copiedKey === "whatsapp" ? "Copiata" : "Copia bozza"}</span>
                  </button>
                </div>
                <pre className="surface-subtle whitespace-pre-wrap p-3 text-[12px] leading-relaxed text-[var(--text-primary)] font-sans">
                  {lead.whatsapp_draft}
                </pre>
              </div>
            </>
          )}

          {tab === "gdpr" && (
            <>
              <div className="surface-panel divide-y divide-[var(--border-hairline)] overflow-hidden">
                <div className="flex items-center justify-between px-3.5 py-2.5">
                  <span className="font-medium">1. Purpose Test (Finalità B2B)</span>
                  <span className={lead.lia_purpose_ok ? "text-emerald-700 font-medium" : "text-red-700 font-medium"}>
                    {lead.lia_purpose_ok ? "SUPERATO" : "BLOCCATO"}
                  </span>
                </div>
                <div className="flex items-center justify-between px-3.5 py-2.5">
                  <span className="font-medium">2. Necessity Test (Dati Minimi)</span>
                  <span className={lead.lia_necessity_ok ? "text-emerald-700 font-medium" : "text-amber-700 font-medium"}>
                    {lead.lia_necessity_ok ? "SUPERATO" : "DA ARRICCHIRE"}
                  </span>
                </div>
                <div className="flex items-center justify-between px-3.5 py-2.5">
                  <span className="font-medium">3. Balancing Test &amp; Blacklist</span>
                  <span className={lead.lia_balancing_ok ? "text-emerald-700 font-medium" : "text-red-700 font-medium"}>
                    {lead.lia_balancing_ok ? "SUPERATO" : "IN BLACKLIST"}
                  </span>
                </div>
              </div>

              <div className="surface-subtle p-3.5 space-y-1.5 text-[12px]">
                <div className="flex items-center gap-1.5 font-semibold text-[var(--text-primary)]">
                  {lead.pec_blocked ? (
                    <ShieldAlert className="h-4 w-4 text-amber-600" />
                  ) : (
                    <ShieldCheck className="h-4 w-4 text-emerald-600" />
                  )}
                  <span>Protezioni ePrivacy &amp; RPO</span>
                </div>
                <div>• Cold outreach su PEC: <strong>Bloccato automaticamente</strong> ({lead.pec || "nessuna PEC presente"})</div>
                <div>• Verifica Registro Pubblico Opposizioni (+39): <strong>{lead.rpo_required ? "Richiesta prima di telemarketing" : "N/A"}</strong></div>
                <div>• Mittente: {lead.gdpr_sender}</div>
              </div>

              <div className="border-t border-[var(--border-hairline)] pt-4">
                <button
                  type="button"
                  disabled={blacklisting || lead.suppressed}
                  onClick={handleBlacklist}
                  className="flex h-9 w-full items-center justify-center gap-2 rounded-md border border-red-200 bg-red-50 text-[12px] font-medium text-red-700 hover:bg-red-100 disabled:opacity-50"
                >
                  <Ban className="h-3.5 w-3.5" />
                  <span>
                    {lead.suppressed
                      ? "Già presente in Suppression List"
                      : blacklisting
                        ? "Inserimento in corso..."
                        : "Aggiungi a Blacklist GDPR (CANCELLAMI)"}
                  </span>
                </button>
              </div>
            </>
          )}
        </div>
      </aside>
    </div>
  );
}
