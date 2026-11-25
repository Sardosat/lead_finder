"use client";

import React, { useEffect, useState } from "react";
import { Ban, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { formatDateIT } from "@/lib/formatters";
import type { SuppressionEntry } from "@/lib/types";

export default function CompliancePage() {
  const [entries, setEntries] = useState<SuppressionEntry[]>([]);
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [vat, setVat] = useState("");
  const [reason, setReason] = useState("CANCELLAMI");
  const [error, setError] = useState("");

  // LIA Tester state
  const [liaCompany, setLiaCompany] = useState("Termoidraulica Etnea Srl");
  const [liaVat, setLiaVat] = useState("IT06200390877");
  const [liaPhone, setLiaPhone] = useState("347 1234567");
  const [liaEmail, setLiaEmail] = useState("impresa@pec.it");
  const [liaRes, setLiaRes] = useState<Record<string, unknown> | null>(null);

  const loadSuppression = () => {
    api
      .getSuppression()
      .then((res) => setEntries(res.entries))
      .catch(() => {});
  };

  useEffect(() => {
    loadSuppression();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const res = await api.addSuppression({
        phone_e164: phone,
        email,
        vat_id: vat,
        reason,
      });
      setEntries(res.entries);
      setPhone("");
      setEmail("");
      setVat("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore aggiunta opt-out.");
    }
  };

  const handleRemove = async (entry: SuppressionEntry) => {
    const res = await api.deleteSuppression({
      phone_e164: entry.phone_e164 || undefined,
      email: entry.email || undefined,
      vat_id: entry.vat_id || undefined,
    });
    setEntries(res.entries);
  };

  const handleTestLia = async () => {
    const res = await api.evaluateLia({
      company_name: liaCompany,
      vat_id: liaVat,
      phone: liaPhone,
      email: liaEmail,
      campaign_purpose: "Proposta commerciale B2B pertinente TecnicoLIVE / CNA",
    });
    setLiaRes(res);
  };

  return (
    <div className="space-y-5 max-w-[1440px]">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left: Suppression List Manager */}
        <div className="lg:col-span-7 space-y-4">
          <form onSubmit={handleAdd} className="surface-panel p-4 space-y-3">
            <div className="flex items-center gap-2">
              <Ban className="h-4 w-4 text-red-600" />
              <h2 className="text-[13px] font-semibold">
                Suppression List Globale (Opt-Out CANCELLAMI)
              </h2>
            </div>
            <p className="text-[12px] text-[var(--text-muted)]">
              Ogni telefono, email o P.IVA inserito viene bloccato automaticamente in tutti gli export CSV/Excel, bozze e webhook.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+39347..."
                className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 font-mono text-[12px]"
              />
              <input
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="email@azienda.it"
                className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px]"
              />
              <input
                type="text"
                value={vat}
                onChange={(e) => setVat(e.target.value)}
                placeholder="IT01234567890"
                className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 font-mono text-[12px]"
              />
              <button
                type="submit"
                className="flex h-8 items-center justify-center gap-1 rounded bg-[#1D4ED8] px-3 text-[12px] font-medium text-white hover:bg-[#1E40AF]"
              >
                <Plus className="h-3.5 w-3.5" />
                <span>Blocca</span>
              </button>
            </div>
            {error && <div className="text-[12px] text-red-700">{error}</div>}
          </form>

          <div className="surface-panel overflow-hidden">
            <div className="border-b border-[var(--border-hairline)] px-4 py-2.5 text-[12px] font-semibold">
              Contatti Bloccati ({entries.length})
            </div>
            <table className="w-full border-collapse text-left text-[12px]">
              <thead className="border-b border-[var(--border-hairline)] bg-[var(--bg-subtle)] text-[11px] uppercase text-[var(--text-muted)]">
                <tr>
                  <th className="px-4 py-2">Telefono E.164</th>
                  <th className="px-3 py-2">Email</th>
                  <th className="px-3 py-2">P.IVA</th>
                  <th className="px-3 py-2">Motivo</th>
                  <th className="px-3 py-2">Data</th>
                  <th className="px-4 py-2 text-right">Rimuovi</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-hairline)]">
                {entries.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-[var(--text-muted)]">
                      Nessun contatto presente nella lista di soppressione.
                    </td>
                  </tr>
                ) : (
                  entries.map((e) => (
                    <tr key={`${e.id}-${e.timestamp_utc}`}>
                      <td className="px-4 py-2 font-mono">{e.phone_e164 || "—"}</td>
                      <td className="px-3 py-2 font-mono">{e.email || "—"}</td>
                      <td className="px-3 py-2 font-mono">{e.vat_id || "—"}</td>
                      <td className="px-3 py-2">{e.reason}</td>
                      <td className="px-3 py-2 text-[11px] text-[var(--text-muted)]">{formatDateIT(e.timestamp_utc)}</td>
                      <td className="px-4 py-2 text-right">
                        <button
                          type="button"
                          onClick={() => handleRemove(e)}
                          className="inline-flex h-6 w-6 items-center justify-center rounded border border-[var(--border-hairline)] text-red-600 hover:bg-red-50"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: 3-Stage LIA Tester */}
        <div className="lg:col-span-5 surface-panel p-4 space-y-3 h-fit">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-[#1D4ED8]" />
            <h2 className="text-[13px] font-semibold">Simulatore GDPR LIA 3 Fasi &amp; Blocco PEC</h2>
          </div>
          <p className="text-[12px] text-[var(--text-muted)]">
            Verifica in tempo reale Purpose Test, Necessity Test, Balancing Test, isolamento PEC e flag RPO (+39).
          </p>

          <div className="space-y-2.5 text-[12px]">
            <input
              type="text"
              value={liaCompany}
              onChange={(e) => setLiaCompany(e.target.value)}
              placeholder="Ragione sociale"
              className="w-full h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5"
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                value={liaVat}
                onChange={(e) => setLiaVat(e.target.value)}
                placeholder="P.IVA"
                className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 font-mono"
              />
              <input
                type="text"
                value={liaPhone}
                onChange={(e) => setLiaPhone(e.target.value)}
                placeholder="Telefono"
                className="h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 font-mono"
              />
            </div>
            <input
              type="text"
              value={liaEmail}
              onChange={(e) => setLiaEmail(e.target.value)}
              placeholder="Email o PEC (es. ditta@pec.it)"
              className="w-full h-8 rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 font-mono"
            />
            <button
              type="button"
              onClick={handleTestLia}
              className="h-8 w-full rounded bg-[#1D4ED8] text-[12px] font-medium text-white hover:bg-[#1E40AF]"
            >
              Valuta Legittimo Interesse (Art. 6.1.f)
            </button>
          </div>

          {liaRes && (
            <pre className="surface-subtle max-h-72 overflow-auto p-3 font-mono text-[11px]">
              {JSON.stringify(liaRes, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}
