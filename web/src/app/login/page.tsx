"use client";

import React, { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Lock, Zap } from "lucide-react";
import { api } from "@/lib/api";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get("next") || "/";

  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.login(username, password);
      router.push(nextPath.startsWith("/") ? nextPath : "/");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Credenziali non valide.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#FAFAFA] px-4">
      <div className="w-full max-w-[380px] surface-panel p-7">
        <div className="flex items-center gap-2.5 mb-6">
          <span className="flex h-8 w-8 items-center justify-center rounded-md bg-[#1D4ED8] text-white">
            <Zap className="h-4 w-4" />
          </span>
          <div>
            <div className="text-[15px] font-semibold tracking-tight text-[#0F172A]">
              Lead Intelligence Engine
            </div>
            <div className="text-[12px] text-[#64748B]">
              Ecosistema TecnicoLIVE · RSK System · MonetizeLab
            </div>
          </div>
        </div>

        <h1 className="text-[16px] font-semibold text-[#0F172A] mb-1">Accesso Operativo</h1>
        <p className="text-[13px] text-[#64748B] mb-5">
          Area protetta per la gestione lead B2B conformi GDPR LIA e export CRM.
        </p>

        {error && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-[12px] font-medium text-[#334155] mb-1">
              Username
            </label>
            <input
              type="text"
              required
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full h-9 rounded-md border border-[#E5E7EB] bg-white px-3 text-[13px] text-[#0F172A] focus:border-[#1D4ED8] focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-[12px] font-medium text-[#334155] mb-1">
              Password
            </label>
            <input
              type="password"
              required
              autoFocus
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Inserisci password dashboard"
              className="w-full h-9 rounded-md border border-[#E5E7EB] bg-white px-3 text-[13px] text-[#0F172A] focus:border-[#1D4ED8] focus:outline-none"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex h-9 w-full items-center justify-center gap-2 rounded-md bg-[#1D4ED8] text-[13px] font-medium text-white hover:bg-[#1E40AF] disabled:opacity-60 transition-colors"
          >
            <Lock className="h-3.5 w-3.5" />
            <span>{loading ? "Verifica in corso..." : "Accedi alla Console"}</span>
          </button>
        </form>

        <div className="mt-5 border-t border-[#E5E7EB] pt-4 text-[11px] text-[#64748B]">
          Credenziali configurabili via <code className="font-mono">AUTH_USERNAME</code> /{" "}
          <code className="font-mono">AUTH_PASSWORD</code> in <code className="font-mono">.env</code>.
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#FAFAFA]" />}>
      <LoginForm />
    </Suspense>
  );
}
