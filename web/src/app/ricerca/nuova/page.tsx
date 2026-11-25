"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, Play, Save, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { formatEur } from "@/lib/formatters";
import type { UpsellProduct } from "@/lib/types";

const TEMPLATES = [
  {
    key: "impiantisti",
    name: "Impiantisti, Termoidraulici & Elettricisti",
    target_vertical: "Termoidraulica, Climatizzazione, Caldaie & Impianti Elettrici",
    ateco_codes: "43.22.01, 43.22.02, 43.21.01",
    queries: "termoidraulica Catania\nassistenza caldaie Acireale\ninstallatore climatizzatori Misterbianco",
    municipalities: "Catania, Acireale, Misterbianco, Paternò, Giarre",
    product_target: "tecnicolive" as UpsellProduct,
    offer_summary:
      "TecnicoLIVE Voice AI H24 chiamate simultanee illimitate (169€/269€/369€) + convenzione CNA Catania 50% 1° anno.",
  },
  {
    key: "agenzie",
    name: "Agenzie Marketing, Web Agency & Creator",
    target_vertical: "Agenzie Marketing Digitale, SEO, Web Agency & Content Creator",
    ateco_codes: "73.11.01, 73.11.02, 74.10.21, 59.11.00",
    queries: "agenzia marketing digitale Catania\nweb agency Palermo\nagenzia comunicazione Milano",
    municipalities: "Catania, Palermo, Milano, Roma",
    product_target: "monetizelab" as UpsellProduct,
    offer_summary:
      "MonetizeLab (monetizelab.online): infrastruttura lead & monetizzazione ricorrente per agenzie e content creator.",
  },
  {
    key: "pmi",
    name: "PMI Locali (Cliniche, Studi Tecnici, Edilizia)",
    target_vertical: "Cliniche Mediche/Estetiche, Studi Tecnici & Rivendite Edili",
    ateco_codes: "86.23.00, 71.12.10, 41.20.00",
    queries: "clinica estetica Catania\nstudio dentistico Acireale\nstudio ingegneria Catania",
    municipalities: "Catania, Acireale, Belpasso, San Giovanni La Punta",
    product_target: "rsksystem" as UpsellProduct,
    offer_summary:
      "RSK System (rsksystem.com): CRM sovrano, Smart Lists dinamiche e automazioni WhatsApp/Email per PMI.",
  },
];

export default function NuovaRicercaPage() {
  const router = useRouter();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Step 1
  const [name, setName] = useState("Campagna Termoidraulica Sicilia Orientale");
  const [vertical, setVertical] = useState("Termoidraulica, Climatizzazione & Impianti");
  const [atecoInput, setAtecoInput] = useState("43.22.01, 43.22.02, 43.21.01");
  const [queriesInput, setQueriesInput] = useState("termoidraulica Catania\nassistenza caldaie Acireale");
  const [productTarget, setProductTarget] = useState<UpsellProduct>("tecnicolive");
  const [offerSummary, setOfferSummary] = useState(
    "TecnicoLIVE Voice AI H24 chiamate simultanee illimitate + associazione CNA Catania 50% 1° anno."
  );

  // Step 2 (Geo-Lock ISTAT)
  const [countryCode, setCountryCode] = useState("IT");
  const [region, setRegion] = useState("Sicilia");
  const [provinceCode, setProvinceCode] = useState("CT");
  const [municipalitiesInput, setMunicipalitiesInput] = useState("Catania, Acireale, Misterbianco, Valverde");
  const [strictCountryLock, setStrictCountryLock] = useState(true);

  // Step 3 (Enrichment Funnel & Budget Cap)
  const [enableL1Audit, setEnableL1Audit] = useState(true);
  const [enableL1Mx, setEnableL1Mx] = useState(true);
  const [enableL1Vies, setEnableL1Vies] = useState(true);
  const [enableL2Ai, setEnableL2Ai] = useState(true);
  const [enableL3Openapi, setEnableL3Openapi] = useState(false);
  const [l3Endpoint, setL3Endpoint] = useState<"IT-start" | "IT-advanced">("IT-start");
  const [maxL3Budget, setMaxL3Budget] = useState(5);
  const [maxResultsPerQuery, setMaxResultsPerQuery] = useState(20);

  const applyTemplate = (tpl: (typeof TEMPLATES)[number]) => {
    setName(tpl.name);
    setVertical(tpl.target_vertical);
    setAtecoInput(tpl.ateco_codes);
    setQueriesInput(tpl.queries);
    setMunicipalitiesInput(tpl.municipalities);
    setProductTarget(tpl.product_target);
    setOfferSummary(tpl.offer_summary);
  };

  const queriesList = queriesInput
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
  const expectedLeads = Math.max(10, Math.min(100, queriesList.length * maxResultsPerQuery));
  const estimatedL2 = enableL2Ai ? expectedLeads * 0.0008 : 0;
  const estimatedL3 = enableL3Openapi ? maxL3Budget : 0;
  const totalEstimated = estimatedL2 + estimatedL3;

  const handleSubmit = async (runNow: boolean) => {
    setError("");
    setSubmitting(true);
    try {
      await api.createSearch({
        name: name.trim(),
        target_vertical: vertical.trim(),
        ateco_codes: atecoInput
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        search_queries: queriesList,
        geo: {
          country_code: countryCode.trim().toUpperCase() || "IT",
          region: region.trim(),
          province_code: provinceCode.trim().toUpperCase(),
          municipalities: municipalitiesInput
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
          istat_codes: [],
          strict_country_lock: strictCountryLock,
        },
        product_target: productTarget,
        offer_summary: offerSummary.trim(),
        enrichment: {
          enable_l1_tech_audit: enableL1Audit,
          enable_l1_mx_check: enableL1Mx,
          enable_l1_vies: enableL1Vies,
          enable_l2_gemini_ai: enableL2Ai,
          enable_l3_openapi_registry: enableL3Openapi,
          l3_endpoint: l3Endpoint,
          max_l3_budget_eur: Number(maxL3Budget) || 0,
        },
        max_results_per_query: maxResultsPerQuery,
        run_now: runNow,
      });
      router.push("/ricerche");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore creazione ricerca.");
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-5">
      {/* Quick Vertical Presets */}
      <div className="surface-panel p-4">
        <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--text-muted)] mb-2">
          Compila da Playbook Ecosistema
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {TEMPLATES.map((tpl) => (
            <button
              key={tpl.key}
              type="button"
              onClick={() => applyTemplate(tpl)}
              className="rounded-md border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-2.5 text-left hover:border-[#1D4ED8] hover:bg-[var(--accent-tint)] transition-colors"
            >
              <div className="text-[12px] font-semibold text-[var(--text-primary)]">{tpl.name}</div>
              <div className="text-[11px] text-[var(--text-muted)] mt-0.5">
                Upsell → {tpl.product_target}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* 3-Step Horizontal Progress */}
      <div className="surface-panel p-5 space-y-5">
        <div className="grid grid-cols-3 border-b border-[var(--border-hairline)] pb-4">
          {[
            { num: 1, title: "1. Settore & Offerta" },
            { num: 2, title: "2. Territorio ISTAT" },
            { num: 3, title: "3. Enrichment & Budget" },
          ].map((st) => {
            const active = step === st.num;
            const done = step > st.num;
            return (
              <button
                key={st.num}
                type="button"
                onClick={() => setStep(st.num as 1 | 2 | 3)}
                className={`flex items-center gap-2 text-left text-[12px] font-medium ${
                  active
                    ? "text-[#1D4ED8]"
                    : done
                      ? "text-emerald-700"
                      : "text-[var(--text-muted)]"
                }`}
              >
                <span
                  className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold ${
                    active
                      ? "bg-[#1D4ED8] text-white"
                      : done
                        ? "bg-emerald-600 text-white"
                        : "bg-[var(--bg-subtle)] text-[var(--text-muted)]"
                  }`}
                >
                  {done ? <Check className="h-3 w-3" /> : st.num}
                </span>
                <span>{st.title}</span>
              </button>
            );
          })}
        </div>

        {step === 1 && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[12px] font-medium mb-1">Nome Ricerca *</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full h-9 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[13px]"
                />
              </div>
              <div>
                <label className="block text-[12px] font-medium mb-1">Prodotto Ecosistema Target</label>
                <select
                  value={productTarget}
                  onChange={(e) => setProductTarget(e.target.value as UpsellProduct)}
                  className="w-full h-9 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[13px]"
                >
                  <option value="tecnicolive">TecnicoLIVE — Impiantisti &amp; Artigiani</option>
                  <option value="rsksystem">RSK System — PMI Generiche CRM/Automazioni</option>
                  <option value="monetizelab">MonetizeLab — Agenzie &amp; Content Creator</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[12px] font-medium mb-1">Verticale / Nicchia *</label>
                <input
                  type="text"
                  value={vertical}
                  onChange={(e) => setVertical(e.target.value)}
                  className="w-full h-9 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[13px]"
                />
              </div>
              <div>
                <label className="block text-[12px] font-medium mb-1">Codici ATECO (separati da virgola)</label>
                <input
                  type="text"
                  value={atecoInput}
                  onChange={(e) => setAtecoInput(e.target.value)}
                  placeholder="43.22.01, 43.21.01"
                  className="w-full h-9 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 font-mono text-[12px]"
                />
              </div>
            </div>

            <div>
              <label className="block text-[12px] font-medium mb-1">
                Query Google Maps / Discovery (una per riga)
              </label>
              <textarea
                rows={3}
                value={queriesInput}
                onChange={(e) => setQueriesInput(e.target.value)}
                className="w-full rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] p-2.5 font-mono text-[12px]"
              />
            </div>

            <div>
              <label className="block text-[12px] font-medium mb-1">
                Offerta / Proposta Valore (usata da L2 AI e conformità LIA)
              </label>
              <textarea
                rows={2}
                value={offerSummary}
                onChange={(e) => setOfferSummary(e.target.value)}
                className="w-full rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] p-2.5 text-[13px]"
              />
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-[12px] font-medium mb-1">Paese ISO (2 lettere)</label>
                <input
                  type="text"
                  maxLength={2}
                  value={countryCode}
                  onChange={(e) => setCountryCode(e.target.value.toUpperCase())}
                  className="w-full h-9 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 font-mono text-[13px]"
                />
              </div>
              <div>
                <label className="block text-[12px] font-medium mb-1">Regione</label>
                <input
                  type="text"
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full h-9 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[13px]"
                />
              </div>
              <div>
                <label className="block text-[12px] font-medium mb-1">Sigla Provincia</label>
                <input
                  type="text"
                  maxLength={2}
                  value={provinceCode}
                  onChange={(e) => setProvinceCode(e.target.value.toUpperCase())}
                  className="w-full h-9 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 font-mono text-[13px]"
                />
              </div>
            </div>

            <div>
              <label className="block text-[12px] font-medium mb-1">
                Comuni ISTAT Target (separati da virgola)
              </label>
              <input
                type="text"
                value={municipalitiesInput}
                onChange={(e) => setMunicipalitiesInput(e.target.value)}
                className="w-full h-9 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[13px]"
              />
            </div>

            <label className="flex items-start gap-2.5 rounded-md border border-emerald-200 bg-emerald-50/70 p-3 text-[12px] text-emerald-900 cursor-pointer">
              <input
                type="checkbox"
                checked={strictCountryLock}
                onChange={(e) => setStrictCountryLock(e.target.checked)}
                className="mt-0.5 accent-emerald-700"
              />
              <div>
                <div className="font-semibold flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-emerald-700" />
                  <span>Geo-Lock Rigoroso Italia / Provincia Attivo</span>
                </div>
                <div className="mt-0.5 text-emerald-800">
                  Blocca automaticamente omonimi esteri (es. Valverde → Ecuador o Spagna rilevati su Clay.com) e capoluoghi fuori provincia.
                </div>
              </div>
            </label>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <div className="divide-y divide-[var(--border-hairline)] rounded-md border border-[var(--border-hairline)]">
              <label className="flex items-center justify-between p-3 cursor-pointer">
                <div>
                  <div className="text-[13px] font-medium">Livello 1 — Tech Audit Sito, MX Email &amp; VIES UE</div>
                  <div className="text-[11px] text-[var(--text-muted)]">
                    SSL, stack CMS, Pixel, CTA WhatsApp, estrazione P.IVA e validazione gratuita VIES/MX
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[12px] font-medium text-emerald-700">Gratuito</span>
                  <input
                    type="checkbox"
                    checked={enableL1Audit && enableL1Vies}
                    onChange={(e) => {
                      setEnableL1Audit(e.target.checked);
                      setEnableL1Mx(e.target.checked);
                      setEnableL1Vies(e.target.checked);
                    }}
                    className="h-4 w-4 accent-[#1D4ED8]"
                  />
                </div>
              </label>

              <label className="flex items-center justify-between p-3 cursor-pointer">
                <div>
                  <div className="text-[13px] font-medium">Livello 2 — Qualificazione Gemini 2.5 Flash AI</div>
                  <div className="text-[11px] text-[var(--text-muted)]">
                    Pain point citati dal sito, ICP score e icebreaker 1-to-1 (fallback deterministico se senza API key)
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[12px] text-[var(--text-secondary)] tabular-nums">
                    ~{formatEur(estimatedL2, 3)}
                  </span>
                  <input
                    type="checkbox"
                    checked={enableL2Ai}
                    onChange={(e) => setEnableL2Ai(e.target.checked)}
                    className="h-4 w-4 accent-[#1D4ED8]"
                  />
                </div>
              </label>

              <div className="p-3 space-y-2.5">
                <label className="flex items-center justify-between cursor-pointer">
                  <div>
                    <div className="text-[13px] font-medium">
                      Livello 3 — Visura Camerale Openapi.com (Solo Tier A/B)
                    </div>
                    <div className="text-[11px] text-[var(--text-muted)]">
                      ATECO ufficiale, stato attività, PEC, SDI e fascia fatturato con tetto massimo di spesa
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    checked={enableL3Openapi}
                    onChange={(e) => setEnableL3Openapi(e.target.checked)}
                    className="h-4 w-4 accent-[#1D4ED8]"
                  />
                </label>

                {enableL3Openapi && (
                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <div>
                      <label className="block text-[11px] text-[var(--text-muted)] mb-1">Endpoint</label>
                      <select
                        value={l3Endpoint}
                        onChange={(e) => setL3Endpoint(e.target.value as "IT-start" | "IT-advanced")}
                        className="w-full h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2 text-[12px]"
                      >
                        <option value="IT-start">IT-start (~0,07 € / visura)</option>
                        <option value="IT-advanced">IT-advanced (~0,25 € / bilancio)</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-[11px] text-[var(--text-muted)] mb-1">Budget Cap Massimo (€)</label>
                      <input
                        type="number"
                        min={0}
                        max={50}
                        step={0.5}
                        value={maxL3Budget}
                        onChange={(e) => setMaxL3Budget(Number(e.target.value))}
                        className="w-full h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px] tabular-nums"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between rounded-md border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-4 py-3 text-[13px]">
              <div>
                <div className="font-medium text-[var(--text-primary)]">Stima Tetto Massima Campagna</div>
                <div className="text-[11px] text-[var(--text-muted)]">
                  Fino a {expectedLeads} aziende ({queriesList.length || 1} query × max {maxResultsPerQuery} risultati)
                </div>
              </div>
              <div className="text-[18px] font-semibold tabular-nums text-[var(--text-primary)]">
                {formatEur(totalEstimated)}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
            {error}
          </div>
        )}

        {/* Footer Controls */}
        <div className="flex items-center justify-between border-t border-[var(--border-hairline)] pt-4">
          <button
            type="button"
            disabled={step === 1}
            onClick={() => setStep((s) => (s > 1 ? ((s - 1) as 1 | 2 | 3) : s))}
            className="flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-hairline)] px-3 text-[12px] font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] disabled:opacity-40"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Indietro</span>
          </button>

          <div className="flex items-center gap-2">
            {step < 3 ? (
              <button
                type="button"
                onClick={() => setStep((s) => ((s + 1) as 1 | 2 | 3))}
                className="flex h-8 items-center gap-1.5 rounded-md bg-[#1D4ED8] px-3.5 text-[12px] font-medium text-white hover:bg-[#1E40AF]"
              >
                <span>Avanti</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            ) : (
              <>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleSubmit(false)}
                  className="flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-3 text-[12px] font-medium text-[var(--text-primary)] hover:bg-[var(--bg-subtle)]"
                >
                  <Save className="h-3.5 w-3.5" />
                  <span>Salva Bozza</span>
                </button>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleSubmit(true)}
                  className="flex h-8 items-center gap-1.5 rounded-md bg-[#1D4ED8] px-3.5 text-[12px] font-medium text-white hover:bg-[#1E40AF] disabled:opacity-60"
                >
                  <Play className="h-3.5 w-3.5" />
                  <span>{submitting ? "Avvio..." : "Salva e Avvia Ora"}</span>
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
