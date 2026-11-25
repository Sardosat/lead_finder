"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AlertTriangle, Archive, Menu, Search } from "lucide-react";
import { api } from "@/lib/api";
import { CommandPalette } from "./CommandPalette";
import { Sidebar } from "./Sidebar";

const PAGE_TITLES: Array<{ prefix: string; title: string; subtitle: string }> = [
  { prefix: "/ricerca/nuova", title: "Nuova Ricerca", subtitle: "Wizard 3-step multi-settore con Geo-Lock ISTAT" },
  { prefix: "/ricerche", title: "Le mie Ricerche", subtitle: "Archivi attivi, playbook verticali e ricerche salvate" },
  { prefix: "/leads", title: "Lead Finder", subtitle: "Tabella intelligente con routing prodotto e conformità GDPR" },
  { prefix: "/trends", title: "Social & Market Radar", subtitle: "Trend locali, pagine FB dei lead, bandi/fiere e post AI (FB/IG/LinkedIn)" },
  { prefix: "/outreach", title: "Sales Hub & Bozze", subtitle: "Revisione Human-in-the-Loop, script e simulatore ROI" },
  { prefix: "/exports", title: "Archivio Export", subtitle: "Cronologia file CSV, Excel, Webhook JSON e Report PDF" },
  { prefix: "/strumenti", title: "Verifica Rapida & Clay Lab", subtitle: "Check VIES, Tech Audit L1, Openapi e benchmark Clay" },
  { prefix: "/compliance", title: "GDPR & Blacklist", subtitle: "Suppression list opt-out, LIA 3 fasi e blocco PEC" },
  { prefix: "/impostazioni", title: "Impostazioni", subtitle: "Stato connettori API, sicurezza e listini ecosistema" },
  { prefix: "/", title: "Panoramica", subtitle: "Stato qualità dati, routing prodotti e attività recenti" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  const isLoginPage = pathname === "/login";

  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [username, setUsername] = useState("admin");
  const [usingDefaultPwd, setUsingDefaultPwd] = useState(false);

  // Hydrate persisted sidebar & theme preferences cleanly (Light default!)
  useEffect(() => {
    try {
      const savedCollapsed = localStorage.getItem("lf_sidebar_collapsed");
      if (savedCollapsed === "true") setCollapsed(true);

      const savedTheme = localStorage.getItem("lf_theme");
      if (savedTheme === "dark") {
        setDarkMode(true);
        document.documentElement.classList.add("dark");
      } else {
        setDarkMode(false);
        document.documentElement.classList.remove("dark");
      }
    } catch {
      // ignore storage errors
    }
  }, []);

  // Verify active session if inside app shell
  useEffect(() => {
    if (isLoginPage) return;
    let cancelled = false;
    api
      .me()
      .then((res) => {
        if (cancelled) return;
        setUsername(res.username || "admin");
        setUsingDefaultPwd(Boolean(res.using_default_password));
      })
      .catch(() => {
        // api helper handles 401 redirect cleanly
      });
    return () => {
      cancelled = true;
    };
  }, [isLoginPage]);

  const toggleCollapse = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("lf_sidebar_collapsed", String(next));
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  const toggleTheme = useCallback(() => {
    setDarkMode((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("lf_theme", next ? "dark" : "light");
      } catch {
        // ignore
      }
      if (next) document.documentElement.classList.add("dark");
      else document.documentElement.classList.remove("dark");
      return next;
    });
  }, []);

  // Global keyboard shortcuts: Cmd+K (Command Palette) & Cmd+B (Sidebar toggle)
  useEffect(() => {
    if (isLoginPage) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdOpen((v) => !v);
      } else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        toggleCollapse();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isLoginPage, toggleCollapse]);

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      // continue redirect
    }
    router.push("/login");
  };

  if (isLoginPage) {
    return <>{children}</>;
  }

  const currentMeta =
    PAGE_TITLES.find((p) => (p.prefix === "/" ? pathname === "/" : pathname.startsWith(p.prefix))) ||
    PAGE_TITLES[PAGE_TITLES.length - 1];

  return (
    <div className="flex min-h-screen bg-[var(--bg-canvas)] text-[var(--text-primary)]">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={toggleCollapse}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
        username={username}
        darkMode={darkMode}
        onToggleTheme={toggleTheme}
        onLogout={handleLogout}
      />

      <div className="flex flex-1 flex-col min-w-0">
        {usingDefaultPwd && (
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-amber-200 bg-amber-50 px-4 py-1.5 text-[12px] text-amber-900 dark:border-amber-900 dark:bg-amber-950/60 dark:text-amber-200">
            <span className="flex flex-wrap items-center gap-1.5 min-w-0">
              <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
              <span>
                Password di sviluppo predefinita attiva. Imposta <code className="font-mono">AUTH_PASSWORD</code> in <code className="font-mono">.env</code> prima di pubblicare online.
              </span>
            </span>
            <Link href="/impostazioni" className="font-medium underline shrink-0">
              Verifica
            </Link>
          </div>
        )}

        {/* Crisp 52px Top Bar */}
        <header className="sticky top-0 z-30 flex h-[52px] items-center justify-between gap-3 border-b border-[var(--border-hairline)] bg-[var(--bg-surface)] px-4 lg:px-6">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Apri menu"
              className="flex h-8 w-8 items-center justify-center rounded-md border border-[var(--border-hairline)] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] lg:hidden"
            >
              <Menu className="h-4 w-4" />
            </button>
            <div className="flex items-baseline gap-2.5 min-w-0">
              <h1 className="truncate text-[14px] font-semibold tracking-tight text-[var(--text-primary)]">
                {currentMeta.title}
              </h1>
              <span className="hidden md:inline truncate text-[12px] text-[var(--text-muted)]">
                {currentMeta.subtitle}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setCmdOpen(true)}
              className="flex h-8 items-center gap-2 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-2.5 text-[12px] text-[var(--text-muted)] hover:border-[var(--border-strong)] hover:text-[var(--text-primary)] transition-colors"
            >
              <Search className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Cerca ovunque…</span>
              <kbd className="rounded border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-muted)]">
                ⌘K
              </kbd>
            </button>

            <Link
              href="/exports"
              className="hidden sm:flex h-8 items-center gap-1.5 rounded-md border border-[var(--border-hairline)] bg-[var(--bg-surface)] px-2.5 text-[12px] font-medium text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] transition-colors"
            >
              <Archive className="h-3.5 w-3.5" />
              <span>Export</span>
            </Link>
          </div>
        </header>

        <main className="flex-1 p-4 lg:p-6 min-w-0">{children}</main>
      </div>

      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />
    </div>
  );
}
