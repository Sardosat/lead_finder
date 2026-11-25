"use client";

import React, { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Globe, Search, ShieldCheck } from "lucide-react";
import { ClayBenchmarkChart } from "@/components/charts/ClayBenchmarkChart";
import { api } from "@/lib/api";
import { formatNumber } from "@/lib/formatters";
import type { ClayBenchmarkResponse } from "@/lib/types";

export default function StrumentiPage() {
  const [tab, setTab] = useState<"workbench" | "benchmark">("workbench");

  // Live Workbench States
  const [vatInput, setVatInput] = useState("IT06200390877");
  const [viesRes, setViesRes] = useState<Record<string, unknown> | null>(null);
  const [viesBusy, setViesBusy] = useState(false);

  const [urlInput, setUrlInput] = useState("https://www.tecnicolive.it");
  const [auditRes, setAuditRes] = useState<Record<string, unknown> | null>(null);
  const [auditBusy, setAuditBusy] = useState(false);

  const [openapiVat, setOpenapiVat] = useState("06200390877");
  const [openapiEndpoint, setOpenapiEndpoint] = useState("IT-start");
  const [openapiBudget, setOpenapiBudget] = useState(1.0);
  const [openapiRes, setOpenapiRes] = useState<Record<string, unknown> | null>(null);
  const [openapiBusy, setOpenapiBusy] = useState(false);

  const [routeCompany, setRouteCompany] = useState("Etna Digital Marketing S.r.l.");
  const [routeCat, setRouteCat] = useState("Agenzia Marketing Digitale");
  const [routeAteco, setRouteAteco] = useState("73.11.01");
  const [routeRes, setRouteRes] = useState<Record<string, unknown> | null>(null);

  const [bench, setBench] = useState<ClayBenchmarkResponse | null>(null);

  useEffect(() => {
    api.getClayBenchmark().then(setBench).catch(() => {});
  }, []);

  const runVies = async () => {
    setViesBusy(true);
    try {
      setViesRes(await api.checkVies(vatInput));
    } finally {
      setViesBusy(false);
    }
  };

  const runAudit = async () => {
    setAuditBusy(true);
    try {
      setAuditRes(await api.runTechAudit(urlInput, true));
    } finally {
      setAuditBusy(false);
    }
  };

  const runOpenapi = async () => {
    setOpenapiBusy(true);
    try {
      setOpenapiRes(await api.queryOpenapi(openapiVat, openapiEndpoint, openapiBudget));
    } finally {
      setOpenapiBusy(false);
    }
  };

  const runRouter = async () => {
    const r = await api.classifyProduct({
      company_name: routeCompany,
      category: routeCat,
      ateco_code: routeAteco,
    });
    setRouteRes(r);
  };

  return (
    <div className="space-y-4 max-w-[1440px]">
      <div className="flex gap-5 border-b border-[var(--border-hairline)] text-[13px]">
        <button
          type="button"
          onClick={() => setTab("workbench")}
          className={`pb-2.5 font-medium border-b-2 transition-colors ${
            tab === "workbench"
              ? "border-[#1D4ED8] text-[#1D4ED8]"
              : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          }`}
        >
          Workbench Live On-Demand
        </button>
        <button
          type="button"
          onClick={() => setTab("benchmark")}
          className={`pb-2.5 font-medium border-b-2 transition-colors ${
            tab === "benchmark"
              ? "border-[#1D4ED8] text-[#1D4ED8]"
              : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          }`}
        >
          Benchmark: Clay.com (esempio.csv) vs Nostro Engine
        </button>
      </div>

      {tab === "workbench" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* VIES UE */}
          <div className="surface-panel p-4 space-y-3">
            <div>
              <h2 className="text-[13px] font-semibold">1. Validazione Fiscale VIES UE (Gratuita)</h2>
              <p className="text-[12px] text-[var(--text-muted)]">
                Pre-check matematico Luhn + interrogazione live Commissione Europea
              </p>
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={vatInput}
                onChange={(e) => setVatInput(e.target.value)}
                placeholder="IT06200390877"
                className="flex-1 h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 font-mono text-[12px]"
              />
              <button
                type="button"
                disabled={viesBusy}
                onClick={runVies}
                className="h-8 rounded bg-[#1D4ED8] px-3 text-[12px] font-medium text-white hover:bg-[#1E40AF] disabled:opacity-50"
              >
                {viesBusy ? "Verifica..." : "Verifica VIES"}
              </button>
            </div>
            {viesRes && (
              <pre className="surface-subtle max-h-48 overflow-auto p-3 font-mono text-[11px]">
                {JSON.stringify(viesRes, null, 2)}
              </pre>
            )}
          </div>

          {/* Tech Audit L1 */}
          <div className="surface-panel p-4 space-y-3">
            <div>
              <h2 className="text-[13px] font-semibold flex items-center gap-1.5">
                <Globe className="h-3.5 w-3.5 text-[#1D4ED8]" />
                <span>2. Livello 1 Tech Audit + DNS MX</span>
              </h2>
              <p className="text-[12px] text-[var(--text-muted)]">
                HTTP, SSL, CMS, Pixel Ads, CTA WhatsApp, Form e validazione record MX
              </p>
            </div>
            <div className="flex gap-2">
              <input
                type="url"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://www.esempio.it"
                className="flex-1 h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px]"
              />
              <button
                type="button"
                disabled={auditBusy}
                onClick={runAudit}
                className="h-8 rounded bg-[#1D4ED8] px-3 text-[12px] font-medium text-white hover:bg-[#1E40AF] disabled:opacity-50"
              >
                {auditBusy ? "Scansione..." : "Scansiona Sito"}
              </button>
            </div>
            {auditRes && (
              <pre className="surface-subtle max-h-48 overflow-auto p-3 font-mono text-[11px]">
                {JSON.stringify({ ...auditRes, text_snippet: undefined }, null, 2)}
              </pre>
            )}
          </div>

          {/* Openapi L3 */}
          <div className="surface-panel p-4 space-y-3">
            <div>
              <h2 className="text-[13px] font-semibold">3. Visura Camerale Openapi.com (Livello 3)</h2>
              <p className="text-[12px] text-[var(--text-muted)]">
                ATECO ufficiale, PEC, SDI e fascia fatturato con protezione budget cap
              </p>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <input
                type="text"
                value={openapiVat}
                onChange={(e) => setOpenapiVat(e.target.value)}
                placeholder="P.IVA / CF"
                className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 font-mono text-[12px]"
              />
              <select
                value={openapiEndpoint}
                onChange={(e) => setOpenapiEndpoint(e.target.value)}
                className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px]"
              >
                <option value="IT-start">IT-start</option>
                <option value="IT-advanced">IT-advanced</option>
              </select>
              <input
                type="number"
                step={0.5}
                min={0}
                max={20}
                value={openapiBudget}
                onChange={(e) => setOpenapiBudget(Number(e.target.value))}
                className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px] tabular-nums"
              />
            </div>
            <button
              type="button"
              disabled={openapiBusy}
              onClick={runOpenapi}
              className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[12px] font-medium hover:bg-[var(--bg-subtle)]"
            >
              {openapiBusy ? "Interrogazione..." : "Esegui Query Openapi"}
            </button>
            {openapiRes && (
              <pre className="surface-subtle max-h-48 overflow-auto p-3 font-mono text-[11px]">
                {JSON.stringify(openapiRes, null, 2)}
              </pre>
            )}
          </div>

          {/* Product Router Simulator */}
          <div className="surface-panel p-4 space-y-3">
            <div>
              <h2 className="text-[13px] font-semibold flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-[#1D4ED8]" />
                <span>4. Simulatore Product Router Ecosistema</span>
              </h2>
              <p className="text-[12px] text-[var(--text-muted)]">
                Verifica come il motore smista ATECO e categorie tra TecnicoLIVE, MonetizeLab e RSK System
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              <input
                type="text"
                value={routeCompany}
                onChange={(e) => setRouteCompany(e.target.value)}
                placeholder="Ragione sociale"
                className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px]"
              />
              <input
                type="text"
                value={routeCat}
                onChange={(e) => setRouteCat(e.target.value)}
                placeholder="Categoria"
                className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px]"
              />
              <input
                type="text"
                value={routeAteco}
                onChange={(e) => setRouteAteco(e.target.value)}
                placeholder="ATECO"
                className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 font-mono text-[12px]"
              />
            </div>
            <button
              type="button"
              onClick={runRouter}
              className="flex h-8 items-center gap-1.5 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[12px] font-medium hover:bg-[var(--bg-subtle)]"
            >
              <Search className="h-3.5 w-3.5" />
              <span>Simula Routing</span>
            </button>
            {routeRes && (
              <div className="surface-subtle p-3 text-[12px] space-y-1">
                <div className="font-semibold text-[var(--text-primary)]">
                  Prodotto Assegnato: {String(routeRes.product_name)} ({String(routeRes.product_url)})
                </div>
                <div className="text-[var(--text-secondary)]">{String(routeRes.rationale)}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "benchmark" && bench && (
        <div className="space-y-4">
          <div className="surface-panel grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-[var(--border-hairline)]">
            <div className="px-4 py-3">
              <div className="text-[11px] uppercase text-[var(--text-muted)]">Clay.com: Fuori Italia su Catania</div>
              <div className="mt-1 text-[20px] font-semibold tabular-nums text-red-700">
                {bench.clay_summary.non_italy_count}/{bench.clay_summary.total_rows}
              </div>
              <div className="text-[11px] text-[var(--text-muted)]">Ecuador &amp; Spagna per omonimia Valverde</div>
            </div>
            <div className="px-4 py-3">
              <div className="text-[11px] uppercase text-[var(--text-muted)]">Clay.com: Tel / Email / P.IVA</div>
              <div className="mt-1 text-[20px] font-semibold tabular-nums">
                {bench.clay_summary.phone_columns} / {bench.clay_summary.email_columns} / {bench.clay_summary.piva_columns}
              </div>
              <div className="text-[11px] text-[var(--text-muted)]">Colonne contatto pronte nel CSV esportato</div>
            </div>
            <div className="px-4 py-3">
              <div className="text-[11px] uppercase text-[var(--text-muted)]">Nostro Engine: Chiamabili E.164</div>
              <div className="mt-1 text-[20px] font-semibold tabular-nums text-emerald-700">
                {formatNumber(bench.engine_summary.outbound_callable)}
              </div>
              <div className="text-[11px] text-[var(--text-muted)]">
                Precisione Italia: {bench.engine_summary.italy_accuracy_pct}%
              </div>
            </div>
            <div className="px-4 py-3">
              <div className="text-[11px] uppercase text-[var(--text-muted)]">Nostro Engine: P.IVA Luhn + PEC</div>
              <div className="mt-1 text-[20px] font-semibold tabular-nums text-[#1D4ED8]">
                {formatNumber(bench.engine_summary.valid_piva_count)}
              </div>
              <div className="text-[11px] text-[var(--text-muted)]">Blocco PEC cold outreach nativo</div>
            </div>
          </div>

          <ClayBenchmarkChart data={bench.comparison_bars} />

          <div className="surface-panel overflow-hidden">
            <div className="border-b border-[var(--border-hairline)] px-4 py-2.5 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-amber-600" />
              <h3 className="text-[13px] font-semibold">
                Errori Geografici Reali Estratti da esempio.csv (Clay.com)
              </h3>
            </div>
            <table className="w-full border-collapse text-left text-[12px]">
              <thead className="border-b border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[11px] uppercase text-[var(--text-muted)]">
                <tr>
                  <th className="px-4 py-2">Azienda</th>
                  <th className="px-3 py-2">Dominio</th>
                  <th className="px-3 py-2">Città rilevata da Clay</th>
                  <th className="px-3 py-2">Paese Reale</th>
                  <th className="px-4 py-2">Dimensione</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-hairline)]">
                {bench.clay_summary.non_italy_examples.map((ex, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2.5 font-medium">{ex.name}</td>
                    <td className="px-3 py-2.5 font-mono text-[11px]">{ex.domain}</td>
                    <td className="px-3 py-2.5">{ex.city} ({ex.state})</td>
                    <td className="px-3 py-2.5 font-medium text-red-700">{ex.country}</td>
                    <td className="px-4 py-2.5">{ex.size}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex items-center gap-2 border-t border-[var(--border-hairline)] bg-emerald-50/70 px-4 py-2 text-[12px] text-emerald-900">
              <CheckCircle2 className="h-4 w-4 text-emerald-700" />
              <span>
                Il Geo-Lock ISTAT/Provincia del nostro motore scarta automaticamente questi falsi positivi prima dell&apos;enrichment.
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
