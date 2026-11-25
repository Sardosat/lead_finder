"use client";

import React, { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Lock, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { formatEur } from "@/lib/formatters";
import type { SettingsStatusResponse } from "@/lib/types";

export default function ImpostazioniPage() {
  const [data, setData] = useState<SettingsStatusResponse | null>(null);

  useEffect(() => {
    api.getSettingsStatus().then(setData).catch(() => {});
  }, []);

  if (!data) {
    return <div className="text-[13px] text-[var(--text-muted)]">Caricamento impostazioni...</div>;
  }

  return (
    <div className="space-y-5 max-w-[1160px]">
      {/* Security Status */}
      <div className="surface-panel p-4 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-[13px] font-semibold">
            <Lock className="h-4 w-4 text-[#1D4ED8]" />
            <span>Sicurezza &amp; Autenticazione Accesso Online</span>
          </div>
          <span className="rounded border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
            Sessione HMAC-SHA256 HttpOnly Attiva ({data.auth.username})
          </span>
        </div>

        {data.auth.using_default_password ? (
          <div className="flex items-start gap-2 rounded border border-amber-200 bg-amber-50 p-3 text-[12px] text-amber-900">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-700 mt-0.5" />
            <div>
              <strong>Password predefinita attiva.</strong> Prima di pubblicare la dashboard su internet (VPS / Railway / Cloudflare), imposta{" "}
              <code className="font-mono">AUTH_USERNAME</code>, <code className="font-mono">AUTH_PASSWORD</code> e{" "}
              <code className="font-mono">AUTH_SECRET</code> nel file <code className="font-mono">.env</code>.
            </div>
          </div>
        ) : (
          <div className="text-[12px] text-emerald-700">
            Credenziali personalizzate configurate correttamente tramite variabili d&apos;ambiente.
          </div>
        )}
      </div>

      {/* Providers Status Table */}
      <div className="surface-panel overflow-hidden">
        <div className="border-b border-[var(--border-hairline)] px-4 py-3">
          <h2 className="text-[13px] font-semibold">Stato Connettori &amp; API</h2>
          <p className="text-[12px] text-[var(--text-muted)]">
            Nessun segreto API viene esposto o trasmesso al browser.
          </p>
        </div>
        <table className="w-full border-collapse text-left text-[13px]">
          <thead className="border-b border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[11px] uppercase text-[var(--text-muted)]">
            <tr>
              <th className="px-4 py-2.5">Provider</th>
              <th className="px-3 py-2.5">Livello</th>
              <th className="px-3 py-2.5">Stato</th>
              <th className="px-3 py-2.5">Modalità</th>
              <th className="px-4 py-2.5">Note</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-hairline)]">
            {data.providers.map((p) => (
              <tr key={p.key}>
                <td className="px-4 py-2.5 font-medium">{p.name}</td>
                <td className="px-3 py-2.5 text-[12px] text-[var(--text-muted)]">{p.category}</td>
                <td className="px-3 py-2.5">
                  {p.configured ? (
                    <span className="inline-flex items-center gap-1 rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[11px] font-medium text-emerald-700">
                      <CheckCircle2 className="h-3 w-3" />
                      <span>Configurato</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 text-[11px] font-medium text-slate-600">
                      Non configurato
                    </span>
                  )}
                </td>
                <td className="px-3 py-2.5 font-mono text-[11px] text-[var(--text-secondary)]">{p.mode}</td>
                <td className="px-4 py-2.5 text-[12px] text-[var(--text-secondary)]">{p.notes}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Sender Identity + Official Pricing Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="surface-panel p-4 space-y-2.5">
          <div className="flex items-center gap-2 text-[13px] font-semibold">
            <ShieldCheck className="h-4 w-4 text-[#1D4ED8]" />
            <span>Identità Mittente &amp; Clausola Opt-Out (AGENTS.md §3)</span>
          </div>
          <div className="text-[12px] text-[var(--text-secondary)]">
            <strong>Mittente:</strong> {data.sender_identity}
          </div>
          <div className="surface-subtle p-2.5 text-[12px] text-[var(--text-secondary)]">
            {data.gdpr_optout_text}
          </div>
        </div>

        <div className="surface-panel p-4 space-y-2">
          <h3 className="text-[13px] font-semibold">
            Listino Ufficiale &amp; Convenzione CNA (-{data.cna_first_year_discount_pct}% 1° Anno)
          </h3>
          <div className="divide-y divide-[var(--border-hairline)] text-[12px] tabular-nums">
            {Object.entries(data.pricing_plans).map(([k, pl]) => (
              <div key={k} className="flex items-center justify-between py-2">
                <span className="font-medium">{pl.name}</span>
                <span>
                  {formatEur(pl.monthly, 0)}/m · {formatEur(pl.annual_monthly)}/m annuale · Setup {formatEur(pl.setup_fee, 0)} ({pl.minutes} min)
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
