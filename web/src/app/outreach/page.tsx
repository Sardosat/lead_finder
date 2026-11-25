"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Check, CheckCircle2, Copy, ExternalLink, Search, ShieldCheck, XCircle } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { formatEur, PRODUCT_BADGE } from "@/lib/formatters";
import type { OutreachDraft, OutreachResponse, SavedSearch } from "@/lib/types";

type OutreachTab = "drafts" | "scripts" | "roi" | "ecosystem";

export default function OutreachPage() {
  const [tab, setTab] = useState<OutreachTab>("drafts");
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [searchId, setSearchId] = useState("ds-outbound-tecnicolive");
  const [productFilter, setProductFilter] = useState("");
  const [q, setQ] = useState("");
  const [data, setData] = useState<OutreachResponse | null>(null);
  const [activeDraft, setActiveDraft] = useState<OutreachDraft | null>(null);
  const [copiedId, setCopiedId] = useState("");

  // ROI Calculator state (STIMA TEORICA)
  const [planKey, setPlanKey] = useState<"base" | "pro" | "business">("pro");
  const [annualBilling, setAnnualBilling] = useState(false);
  const [technicians, setTechnicians] = useState(2);
  const [missedPerWeek, setMissedPerWeek] = useState(8);
  const [avgTicket, setAvgTicket] = useState(140);
  const [convPct, setConvPct] = useState(30);

  const loadDrafts = useCallback(async () => {
    const res = await api.getOutreachDrafts({
      search_id: searchId,
      product: productFilter,
      q,
      page_size: 20,
    });
    setData(res);
    setActiveDraft((prev) => res.drafts.find((d) => d.lead_key === prev?.lead_key) || res.drafts[0] || null);
  }, [searchId, productFilter, q]);

  useEffect(() => {
    api
      .getSearches()
      .then((r) => setSearches(r.searches.filter((s) => s.leads_count > 0)))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadDrafts().catch(() => {});
  }, [loadDrafts]);

  const copyText = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(""), 1400);
    } catch {
      // ignore
    }
  };

  const handleSetApproval = async (draft: OutreachDraft, status: "APPROVED" | "SKIPPED" | "PENDING") => {
    await api.approveOutreachDraft({
      lead_key: draft.lead_key,
      company_name: draft.company_name,
      channel: "whatsapp",
      status,
    });
    await loadDrafts();
  };

  // ROI Math (explicitly STIMA TEORICA)
  const plans = data?.pricing_plans;
  const selectedPlan = plans ? plans[planKey] : { name: "Piano Pro", monthly: 269, annual_monthly: 215.2, setup_fee: 599, minutes: 300, target: "", annual_total: 2582.4 };
  const monthlyRate = annualBilling ? selectedPlan.annual_monthly : selectedPlan.monthly;
  const annualServiceCost = monthlyRate * 12 + selectedPlan.setup_fee;
  const missedMonth = missedPerWeek * 4 * technicians;
  const lostRevenueMonth = missedMonth * (convPct / 100) * avgTicket;
  const lostRevenueYear = lostRevenueMonth * 12;
  const netGainYear1 = lostRevenueYear - annualServiceCost;
  const roiChartData = [
    { label: "Fatturato Perso Stimato/Anno", value: Math.round(lostRevenueYear) },
    { label: "Costo TecnicoLIVE 1° Anno (c/Setup)", value: Math.round(annualServiceCost) },
    { label: "Impatto Netto Teorico 1° Anno", value: Math.round(Math.max(0, netGainYear1)) },
  ];

  return (
    <div className="space-y-4 max-w-[1440px]">
      {/* Sub-Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border-hairline)]">
        <div className="flex gap-5 text-[13px]">
          {[
            { id: "drafts", label: "Coda Bozze 1-to-1 (HITL)" },
            { id: "scripts", label: "Script & Battlecard Obiezioni" },
            { id: "roi", label: "Calcolatore ROI (Stima Teorica)" },
            { id: "ecosystem", label: "Ecosistema & Listino Ufficiale" },
          ].map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id as OutreachTab)}
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

        {data && tab === "drafts" && (
          <div className="pb-2 text-[12px] text-[var(--text-muted)] tabular-nums">
            <strong className="text-[var(--text-primary)]">{data.approved_count}</strong> bozze approvate su{" "}
            {data.total} contattabili
          </div>
        )}
      </div>

      {/* TAB 1: BOZZE 1-TO-1 HITL */}
      {tab === "drafts" && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={searchId}
              onChange={(e) => setSearchId(e.target.value)}
              className="h-8 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px]"
            >
              {searches.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
            <select
              value={productFilter}
              onChange={(e) => setProductFilter(e.target.value)}
              className="h-8 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px]"
            >
              <option value="">Tutti i Prodotti</option>
              <option value="tecnicolive">TecnicoLIVE</option>
              <option value="rsksystem">RSK System</option>
              <option value="monetizelab">MonetizeLab</option>
            </select>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[var(--text-muted)]" />
              <input
                type="text"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Cerca azienda..."
                className="h-8 w-52 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] pl-8 pr-2.5 text-[12px]"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Master List */}
            <div className="lg:col-span-5 surface-panel divide-y divide-[var(--border-hairline)] max-h-[620px] overflow-y-auto">
              {(data?.drafts || []).map((d) => {
                const isSelected = activeDraft?.lead_key === d.lead_key;
                return (
                  <button
                    key={d.lead_id}
                    type="button"
                    onClick={() => setActiveDraft(d)}
                    className={`w-full px-3.5 py-2.5 text-left transition-colors ${
                      isSelected ? "bg-[var(--accent-tint)]" : "hover:bg-[var(--bg-subtle)]"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-[13px] font-medium text-[var(--text-primary)]">
                        {d.company_name}
                      </span>
                      <span
                        className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium ${
                          d.approval_status === "APPROVED"
                            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                            : d.approval_status === "SKIPPED"
                              ? "border-slate-200 bg-slate-100 text-slate-600"
                              : "border-amber-200 bg-amber-50 text-amber-800"
                        }`}
                      >
                        {d.approval_status === "APPROVED"
                          ? "Approvata"
                          : d.approval_status === "SKIPPED"
                            ? "Saltata"
                            : "In revisione"}
                      </span>
                    </div>
                    <div className="mt-0.5 flex items-center justify-between text-[11px] text-[var(--text-muted)]">
                      <span>
                        {d.city} · {d.phone_e164 || d.email}
                      </span>
                      <span>Tier {d.tier_code} ({d.icp_score})</span>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Draft Detail */}
            <div className="lg:col-span-7 surface-panel p-5 space-y-4">
              {activeDraft ? (
                <>
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[var(--border-hairline)] pb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-[15px] font-semibold">{activeDraft.company_name}</h2>
                        <span
                          className={`rounded border px-1.5 py-0.5 text-[10px] font-medium ${
                            PRODUCT_BADGE[activeDraft.recommended_product].className
                          }`}
                        >
                          {activeDraft.recommended_product_name}
                        </span>
                      </div>
                      <div className="text-[12px] text-[var(--text-muted)] mt-0.5">
                        {activeDraft.city} · Tel: <span className="font-mono">{activeDraft.phone_e164 || "—"}</span> · Email:{" "}
                        <span className="font-mono">{activeDraft.email || "—"}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => handleSetApproval(activeDraft, "SKIPPED")}
                        className="flex h-8 items-center gap-1 rounded border border-[var(--border-hairline)] px-2.5 text-[12px] hover:bg-[var(--bg-subtle)]"
                      >
                        <XCircle className="h-3.5 w-3.5 text-[var(--text-muted)]" />
                        <span>Salta</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleSetApproval(activeDraft, "APPROVED")}
                        className="flex h-8 items-center gap-1 rounded bg-[#1D4ED8] px-3 text-[12px] font-medium text-white hover:bg-[#1E40AF]"
                      >
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        <span>Approva Bozza (HITL)</span>
                      </button>
                    </div>
                  </div>

                  {/* GDPR Checks */}
                  <div className="flex flex-wrap items-center gap-3 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3 py-2 text-[11px]">
                    <span className="flex items-center gap-1 font-medium">
                      <ShieldCheck className="h-3.5 w-3.5 text-emerald-700" />
                      Controllo Conformità:
                    </span>
                    <span>{activeDraft.checks.has_sender ? "✓ Mittente Trasparente" : "⚠ Mittente"}</span>
                    <span>{activeDraft.checks.has_optout ? "✓ Opt-Out CANCELLAMI" : "⚠ Opt-Out"}</span>
                    <span>{activeDraft.checks.no_pec_in_email ? "✓ Zero PEC outbound" : "⚠ PEC"}</span>
                    {activeDraft.checks.rpo_required && (
                      <span className="text-amber-800 font-medium">• Avviso RPO +39</span>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[12px] font-semibold">Messaggio WhatsApp / Testo Outbound (Solo Bozza)</span>
                      <button
                        type="button"
                        onClick={() => copyText(activeDraft.lead_id, activeDraft.whatsapp_draft)}
                        className="flex items-center gap-1 text-[11px] font-medium text-[#1D4ED8] hover:underline"
                      >
                        {copiedId === activeDraft.lead_id ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                        <span>{copiedId === activeDraft.lead_id ? "Copiato" : "Copia bozza"}</span>
                      </button>
                    </div>
                    <pre className="surface-subtle whitespace-pre-wrap p-3.5 font-sans text-[12px] leading-relaxed">
                      {activeDraft.whatsapp_draft}
                    </pre>
                  </div>
                </>
              ) : (
                <div className="py-12 text-center text-[13px] text-[var(--text-muted)]">
                  Seleziona un lead dalla lista a sinistra per revisionare la bozza.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: SCRIPT & OBIEZIONI */}
      {tab === "scripts" && data && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="space-y-4">
            {data.scripts.map((sc) => (
              <div key={sc.id} className="surface-panel p-4 space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-[13px] font-semibold text-[var(--text-primary)]">{sc.title}</h3>
                  <button
                    type="button"
                    onClick={() => copyText(sc.id, sc.body)}
                    className="flex items-center gap-1 text-[11px] font-medium text-[#1D4ED8] hover:underline"
                  >
                    {copiedId === sc.id ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                    <span>Copia</span>
                  </button>
                </div>
                <pre className="surface-subtle whitespace-pre-wrap p-3 font-sans text-[12px] leading-relaxed text-[var(--text-secondary)]">
                  {sc.body}
                </pre>
              </div>
            ))}
          </div>

          <div className="surface-panel overflow-hidden">
            <div className="border-b border-[var(--border-hairline)] px-4 py-3">
              <h3 className="text-[13px] font-semibold text-[var(--text-primary)]">
                Battlecard Gestione Obiezioni
              </h3>
            </div>
            <div className="divide-y divide-[var(--border-hairline)]">
              {data.objections.map((ob, i) => (
                <div key={i} className="p-4 space-y-1.5">
                  <div className="text-[13px] font-semibold text-[var(--text-primary)]">
                    &ldquo;{ob.objection}&rdquo;
                  </div>
                  <p className="text-[12px] leading-relaxed text-[var(--text-secondary)]">{ob.rebuttal}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: ROI CALCULATOR */}
      {tab === "roi" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-5 surface-panel p-5 space-y-4">
            <div className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] font-medium text-amber-900">
              STIMA TEORICA / MODELLO PREDITTIVO (AGENTS.md §2) — Simulazione matematica sui parametri del cliente.
            </div>

            <div className="space-y-3 text-[13px]">
              <div>
                <label className="block text-[12px] font-medium mb-1">Piano TecnicoLIVE</label>
                <select
                  value={planKey}
                  onChange={(e) => setPlanKey(e.target.value as "base" | "pro" | "business")}
                  className="w-full h-9 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px]"
                >
                  <option value="base">Piano Base — 169€/m (+399€ Setup, 150 min)</option>
                  <option value="pro">Piano Pro (Più Scelto) — 269€/m (+599€ Setup, 300 min)</option>
                  <option value="business">Piano Business — 369€/m (+699€ Setup, 500 min)</option>
                </select>
              </div>

              <label className="flex items-center gap-2 text-[12px] cursor-pointer">
                <input
                  type="checkbox"
                  checked={annualBilling}
                  onChange={(e) => setAnnualBilling(e.target.checked)}
                  className="accent-[#1D4ED8]"
                />
                <span>Fatturazione Annuale (-20% sul canone mensile)</span>
              </label>

              <div>
                <div className="flex justify-between text-[12px] mb-1">
                  <span>Numero tecnici / furgoni</span>
                  <strong className="tabular-nums">{technicians}</strong>
                </div>
                <input
                  type="range"
                  min={1}
                  max={15}
                  value={technicians}
                  onChange={(e) => setTechnicians(Number(e.target.value))}
                  className="w-full accent-[#1D4ED8]"
                />
              </div>

              <div>
                <div className="flex justify-between text-[12px] mb-1">
                  <span>Chiamate perse / settimana per tecnico</span>
                  <strong className="tabular-nums">{missedPerWeek}</strong>
                </div>
                <input
                  type="range"
                  min={2}
                  max={25}
                  value={missedPerWeek}
                  onChange={(e) => setMissedPerWeek(Number(e.target.value))}
                  className="w-full accent-[#1D4ED8]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[12px] font-medium mb-1">Ticket medio (€)</label>
                  <input
                    type="number"
                    min={50}
                    max={1500}
                    step={10}
                    value={avgTicket}
                    onChange={(e) => setAvgTicket(Number(e.target.value))}
                    className="w-full h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px] tabular-nums"
                  />
                </div>
                <div>
                  <label className="block text-[12px] font-medium mb-1">% Conversione</label>
                  <input
                    type="number"
                    min={5}
                    max={90}
                    value={convPct}
                    onChange={(e) => setConvPct(Number(e.target.value))}
                    className="w-full h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px] tabular-nums"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="lg:col-span-7 space-y-4">
            <div className="surface-panel grid grid-cols-3 divide-x divide-[var(--border-hairline)]">
              <div className="p-4">
                <div className="text-[11px] uppercase text-[var(--text-muted)]">Perdita Stimata/Anno</div>
                <div className="mt-1 text-[20px] font-semibold tabular-nums text-red-700">
                  {formatEur(lostRevenueYear, 0)}
                </div>
              </div>
              <div className="p-4">
                <div className="text-[11px] uppercase text-[var(--text-muted)]">Costo 1° Anno (c/Setup)</div>
                <div className="mt-1 text-[20px] font-semibold tabular-nums text-[var(--text-primary)]">
                  {formatEur(annualServiceCost, 0)}
                </div>
              </div>
              <div className="p-4">
                <div className="text-[11px] uppercase text-[var(--text-muted)]">Impatto Netto 1° Anno</div>
                <div className="mt-1 text-[20px] font-semibold tabular-nums text-emerald-700">
                  {formatEur(netGainYear1, 0)}
                </div>
              </div>
            </div>

            <div className="surface-panel p-4 min-w-0">
              <h3 className="text-[13px] font-semibold mb-2">Confronto Valore Recuperabile vs Costo (Stima Teorica)</h3>
              <div className="h-[240px] w-full min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={roiChartData} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
                    <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#475569" }} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
                    <Tooltip formatter={(v: number) => formatEur(v, 0)} />
                    <Bar dataKey="value" fill="#1D4ED8" radius={[4, 4, 0, 0]} barSize={48} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: ECOSYSTEM */}
      {tab === "ecosystem" && data && (
        <div className="space-y-4">
          <div className="surface-panel overflow-hidden">
            <div className="border-b border-[var(--border-hairline)] px-4 py-3">
              <h3 className="text-[13px] font-semibold">Bridge di Destinazione Ecosistema</h3>
            </div>
            <table className="w-full border-collapse text-left text-[13px]">
              <thead className="border-b border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[11px] uppercase text-[var(--text-muted)]">
                <tr>
                  <th className="px-4 py-2.5">Prodotto</th>
                  <th className="px-3 py-2.5">Target Assegnato</th>
                  <th className="px-3 py-2.5">Posizionamento</th>
                  <th className="px-4 py-2.5">Dominio</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-hairline)]">
                {data.products.map((p) => (
                  <tr key={p.key}>
                    <td className="px-4 py-3 font-semibold">{p.name}</td>
                    <td className="px-3 py-3 text-[12px] text-[var(--text-secondary)]">{p.target}</td>
                    <td className="px-3 py-3 text-[12px] text-[var(--text-secondary)] max-w-md">{p.core_pitch}</td>
                    <td className="px-4 py-3">
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 text-[12px] font-medium text-[#1D4ED8] hover:underline"
                      >
                        <span>{p.url.replace("https://", "")}</span>
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="surface-panel overflow-hidden">
            <div className="border-b border-[var(--border-hairline)] px-4 py-3 flex items-center justify-between">
              <h3 className="text-[13px] font-semibold">Listino Ufficiale TecnicoLIVE</h3>
              <span className="text-[12px] font-medium text-[#1D4ED8]">
                Convenzione CNA Catania: {data.cna_first_year_discount_pct}% quota associativa 1° anno · -{data.annual_discount_pct}% annuale
              </span>
            </div>
            <table className="w-full border-collapse text-left text-[13px]">
              <thead className="border-b border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[11px] uppercase text-[var(--text-muted)]">
                <tr>
                  <th className="px-4 py-2.5">Piano</th>
                  <th className="px-3 py-2.5">Canone Mensile</th>
                  <th className="px-3 py-2.5">Annuale (-20%)</th>
                  <th className="px-3 py-2.5">Setup Una Tantum</th>
                  <th className="px-4 py-2.5">Minuti Inclusi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-hairline)] tabular-nums">
                {Object.entries(data.pricing_plans).map(([k, pl]) => (
                  <tr key={k}>
                    <td className="px-4 py-3 font-medium">
                      {pl.name} <span className="text-[11px] text-[var(--text-muted)] font-normal">({pl.target})</span>
                    </td>
                    <td className="px-3 py-3">{formatEur(pl.monthly, 0)} + IVA</td>
                    <td className="px-3 py-3">{formatEur(pl.annual_monthly)}/mese</td>
                    <td className="px-3 py-3">{formatEur(pl.setup_fee, 0)}</td>
                    <td className="px-4 py-3">{pl.minutes} min/mese · Illimitate simultanee</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
