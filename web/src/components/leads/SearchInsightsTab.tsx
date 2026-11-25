"use client";

import React from "react";
import {
  AlertTriangle,
  Award,
  Building2,
  CheckCircle2,
  Cpu,
  Flame,
  Megaphone,
  PhoneCall,
  ShieldAlert,
  Sparkles,
  Target,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PRODUCT_BADGE, TIER_BADGE } from "@/lib/formatters";
import type { LeadItem, LeadsInsights } from "@/lib/types";

interface SearchInsightsTabProps {
  items: LeadItem[];
  insights?: LeadsInsights;
  total: number;
  loading: boolean;
  onInspectLead: (lead: LeadItem) => void;
}

const PRODUCT_COLORS: Record<string, string> = {
  tecnicolive: "#1D4ED8",
  rsksystem: "#0F766E",
  monetizelab: "#7C3AED",
};

export function SearchInsightsTab({
  items,
  insights,
  total,
  loading,
  onInspectLead,
}: SearchInsightsTabProps) {
  if (loading) {
    return (
      <div className="surface-panel p-8 text-center text-[13px] text-[var(--text-muted)]">
        Caricamento analisi Pain Points, Punti Deboli e Punti di Forza...
      </div>
    );
  }

  const topPains = insights?.top_pain_points || [];
  const topWeaks = insights?.top_weak_points || [];
  const topStrengths = insights?.top_strengths || [];
  const productBreakdown = insights?.product_breakdown || [];
  const sizeBreakdown = insights?.size_breakdown || [];

  return (
    <div className="space-y-4">
      {/* KPI Summary Bar con icone colorate */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="surface-panel p-3.5 flex items-center gap-3 border-l-4 border-l-red-500">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-red-50 text-red-600">
            <Flame className="h-5 w-5" />
          </span>
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
              Pain Points / Lead
            </div>
            <div className="text-[18px] font-bold text-[var(--text-primary)] tabular-nums">
              {insights?.avg_pain_per_lead ?? 0}
            </div>
            <div className="text-[11px] text-red-700">Leve dirette da attaccare</div>
          </div>
        </div>

        <div className="surface-panel p-3.5 flex items-center gap-3 border-l-4 border-l-amber-500">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-600">
            <AlertTriangle className="h-5 w-5" />
          </span>
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
              Weak Points / Lead
            </div>
            <div className="text-[18px] font-bold text-[var(--text-primary)] tabular-nums">
              {insights?.avg_weak_per_lead ?? 0}
            </div>
            <div className="text-[11px] text-amber-700">Gap digitali e di contatto</div>
          </div>
        </div>

        <div className="surface-panel p-3.5 flex items-center gap-3 border-l-4 border-l-emerald-500">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600">
            <CheckCircle2 className="h-5 w-5" />
          </span>
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
              Strengths / Lead
            </div>
            <div className="text-[18px] font-bold text-[var(--text-primary)] tabular-nums">
              {insights?.avg_strength_per_lead ?? 0}
            </div>
            <div className="text-[11px] text-emerald-700">Asset reali su cui far leva</div>
          </div>
        </div>

        <div className="surface-panel p-3.5 flex items-center gap-3 border-l-4 border-l-blue-600">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
            <Target className="h-5 w-5" />
          </span>
          <div>
            <div className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
              Lead Analizzati
            </div>
            <div className="text-[18px] font-bold text-[var(--text-primary)] tabular-nums">
              {total.toLocaleString("it-IT")}
            </div>
            <div className="text-[11px] text-blue-700">Zero Hallucination · Pre-Call</div>
          </div>
        </div>
      </div>

      {/* Grafici Esplicativi */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Grafico 1: Top Pain Points da Attaccare */}
        <div className="surface-panel p-4 min-w-0">
          <div className="mb-2 flex items-center gap-2">
            <Flame className="h-4 w-4 text-red-600" />
            <h3 className="text-[13px] font-semibold text-[var(--text-primary)]">
              Pain Points Attaccabili
            </h3>
          </div>
          <p className="mb-3 text-[11px] text-[var(--text-muted)]">
            Problemi operativi e di conversione più frequenti nei risultati filtrati
          </p>
          <div className="h-[220px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topPains.slice(0, 5)} layout="vertical" margin={{ top: 4, right: 20, left: 4, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="title"
                  width={150}
                  tick={{ fontSize: 10, fill: "#334155" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip contentStyle={{ fontSize: "12px", borderRadius: "6px" }} />
                <Bar dataKey="count" name="Aziende" fill="#DC2626" radius={[0, 4, 4, 0]} barSize={18} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Grafico 2: Weak Points vs Strengths */}
        <div className="surface-panel p-4 min-w-0">
          <div className="mb-2 flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-amber-600" />
            <h3 className="text-[13px] font-semibold text-[var(--text-primary)]">
              Punti Deboli &amp; Punti di Forza
            </h3>
          </div>
          <p className="mb-3 text-[11px] text-[var(--text-muted)]">
            Gap digitali rilevati (ambra) vs asset reali aziendali (verde)
          </p>
          <div className="h-[220px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={[
                  ...topWeaks.slice(0, 3).map((w) => ({ name: w.title, count: w.count, fill: "#D97706" })),
                  ...topStrengths.slice(0, 3).map((s) => ({ name: s.title, count: s.count, fill: "#059669" })),
                ]}
                layout="vertical"
                margin={{ top: 4, right: 20, left: 4, bottom: 4 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={150}
                  tick={{ fontSize: 10, fill: "#334155" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip contentStyle={{ fontSize: "12px", borderRadius: "6px" }} />
                <Bar dataKey="count" name="Aziende" radius={[0, 4, 4, 0]} barSize={16}>
                  {[
                    ...topWeaks.slice(0, 3).map((w) => ({ key: w.title, fill: "#D97706" })),
                    ...topStrengths.slice(0, 3).map((s) => ({ key: s.title, fill: "#059669" })),
                  ].map((entry) => (
                    <Cell key={entry.key} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Grafico 3: Cosa Vendere & Dimensione */}
        <div className="surface-panel p-4 min-w-0">
          <div className="mb-2 flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-[#1D4ED8]" />
            <h3 className="text-[13px] font-semibold text-[var(--text-primary)]">
              Cosa Vendere &amp; Dimensione
            </h3>
          </div>
          <p className="mb-3 text-[11px] text-[var(--text-muted)]">
            Prodotti consigliati e struttura aziendale dei lead in vista
          </p>
          <div className="h-[130px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={productBreakdown} margin={{ top: 4, right: 12, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                <XAxis dataKey="product_name" tick={{ fontSize: 11, fill: "#334155" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#64748B" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ fontSize: "12px", borderRadius: "6px" }} />
                <Bar dataKey="count" name="Lead" radius={[4, 4, 0, 0]} barSize={32}>
                  {productBreakdown.map((p) => (
                    <Cell key={p.product_key} fill={PRODUCT_COLORS[p.product_key] || "#1D4ED8"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {sizeBreakdown.slice(0, 4).map((sz) => (
              <span
                key={sz.label}
                className="inline-flex items-center gap-1 rounded border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-secondary)]"
              >
                <Building2 className="h-3 w-3 text-blue-600" />
                {sz.label}: <strong>{sz.count}</strong>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Record Pre-Chiamata per ciascun Lead in pagina */}
      <div className="space-y-2.5">
        <h3 className="text-[13px] font-semibold text-[var(--text-primary)]">
          Dossier Pre-Chiamata per Lead (Cosa Vendergli e Perché)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {items.map((lead) => {
            const prodBadge = PRODUCT_BADGE[lead.recommended_product] || PRODUCT_BADGE.rsksystem;
            const tierBadge = TIER_BADGE[lead.tier_code] || TIER_BADGE.C;
            const pains = lead.pain_signals || [];
            const weaks = lead.weak_points || [];
            const strs = lead.strengths || [];
            const brief = lead.sales_brief;

            return (
              <div
                key={lead.id}
                onClick={() => onInspectLead(lead)}
                className="surface-panel p-4 space-y-3 cursor-pointer hover:border-[#1D4ED8] transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-1.5 mb-1">
                      <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${tierBadge.className}`}>
                        {tierBadge.label} · {lead.icp_score}
                      </span>
                      <span className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${prodBadge.className}`}>
                        {prodBadge.label}
                      </span>
                      {lead.company_size_label && (
                        <span className="inline-flex items-center gap-1 rounded border border-slate-200 bg-slate-50 px-1.5 py-0.5 text-[10px] font-medium text-slate-700">
                          <Building2 className="h-2.5 w-2.5 text-blue-600" />
                          {lead.company_size_label}
                        </span>
                      )}
                    </div>
                    <h4 className="truncate text-[14px] font-semibold text-[var(--text-primary)]">
                      {lead.company_name}
                    </h4>
                    <p className="truncate text-[11px] text-[var(--text-muted)]">
                      {lead.city || "N/D"} · {lead.niche} · {lead.phone_e164 || "Tel da arricchire"}
                    </p>
                  </div>
                  <span className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-2 py-1 text-[11px] font-medium text-[#1D4ED8] shrink-0">
                    <PhoneCall className="h-3 w-3" />
                    <span>Pre-Call</span>
                  </span>
                </div>

                {brief && (
                  <div className="rounded-md border border-blue-200 bg-blue-50/70 p-2.5 text-[12px] space-y-1">
                    <div className="flex items-center gap-1.5 font-semibold text-blue-900">
                      <Target className="h-3.5 w-3.5 text-blue-700 shrink-0" />
                      <span className="truncate">{brief.recommended_plan || brief.product_name}</span>
                    </div>
                    <p className="text-[11px] text-slate-700 line-clamp-2">{brief.why_sell}</p>
                    <div className="flex items-center gap-1.5 text-[11px] text-slate-600">
                      <Cpu className="h-3 w-3 text-purple-600 shrink-0" />
                      <span>Tech: {brief.tech_maturity_label}</span>
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap gap-1.5 text-[11px]">
                  {pains.slice(0, 2).map((p) => (
                    <span
                      key={p.id}
                      className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2 py-0.5 font-medium text-red-700"
                    >
                      <Flame className="h-3 w-3" />
                      {p.title}
                    </span>
                  ))}
                  {weaks.slice(0, 2).map((w) => (
                    <span
                      key={w.id}
                      className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 font-medium text-amber-800"
                    >
                      <AlertTriangle className="h-3 w-3" />
                      {w.title}
                    </span>
                  ))}
                  {strs.slice(0, 2).map((s) => (
                    <span
                      key={s.id}
                      className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 font-medium text-emerald-800"
                    >
                      {s.id === "str_ads_active" ? (
                        <Megaphone className="h-3 w-3" />
                      ) : (
                        <Award className="h-3 w-3" />
                      )}
                      {s.title}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
