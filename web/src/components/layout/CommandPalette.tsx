"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Archive, ArrowRight, FolderSearch, Plus, Search, X } from "lucide-react";
import { api } from "@/lib/api";
import type { ExportRecord, SavedSearch } from "@/lib/types";
import { NAV_GROUPS } from "./Sidebar";

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

interface CommandItem {
  id: string;
  group: string;
  label: string;
  subtitle: string;
  href: string;
  icon: React.ReactNode;
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [exportsList, setExportsList] = useState<ExportRecord[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setSelectedIdx(0);
    let cancelled = false;
    Promise.all([
      api.getSearches().catch(() => ({ searches: [] })),
      api.getExports().catch(() => ({ exports: [] })),
    ]).then(([sRes, eRes]) => {
      if (cancelled) return;
      setSearches(sRes.searches.slice(0, 8));
      setExportsList(eRes.exports.slice(0, 6));
    });
    return () => {
      cancelled = true;
    };
  }, [open]);

  const allItems = useMemo<CommandItem[]>(() => {
    const navItems: CommandItem[] = [
      {
        id: "cta-new-search",
        group: "Azioni Rapide",
        label: "Nuova Ricerca Lead Multi-Settore",
        subtitle: "Apri il wizard 3-step con Geo-Lock ISTAT",
        href: "/ricerca/nuova",
        icon: <Plus className="h-4 w-4 text-[#1D4ED8]" />,
      },
      ...NAV_GROUPS.flatMap((g) =>
        g.items.map((it) => {
          const Icon = it.icon;
          return {
            id: `nav-${it.href}`,
            group: g.title,
            label: it.label,
            subtitle: `Vai a ${it.label}`,
            href: it.href,
            icon: <Icon className="h-4 w-4 text-[var(--text-muted)]" />,
          };
        })
      ),
    ];

    const searchItems: CommandItem[] = searches.map((s) => ({
      id: `srch-${s.id}`,
      group: "Le mie Ricerche",
      label: s.name,
      subtitle: `${s.leads_count} aziende · ${s.callable_count} chiamabili`,
      href: `/leads?search_id=${encodeURIComponent(s.id)}`,
      icon: <FolderSearch className="h-4 w-4 text-[var(--text-muted)]" />,
    }));

    const expItems: CommandItem[] = exportsList.map((e) => ({
      id: `exp-${e.id}`,
      group: "Archivio Export",
      label: e.filename,
      subtitle: `${e.format} · ${e.row_count} righe`,
      href: "/exports",
      icon: <Archive className="h-4 w-4 text-[var(--text-muted)]" />,
    }));

    return [...navItems, ...searchItems, ...expItems];
  }, [searches, exportsList]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return allItems;
    return allItems.filter(
      (i) =>
        i.label.toLowerCase().includes(q) ||
        i.subtitle.toLowerCase().includes(q) ||
        i.group.toLowerCase().includes(q)
    );
  }, [allItems, query]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIdx((i) => Math.min(filtered.length - 1, i + 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIdx((i) => Math.max(0, i - 1));
      } else if (e.key === "Enter" && filtered[selectedIdx]) {
        e.preventDefault();
        router.push(filtered[selectedIdx].href);
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, filtered, selectedIdx, router, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[12vh] px-4">
      <div className="fixed inset-0 bg-slate-900/35" onClick={onClose} />
      <div className="relative z-10 w-full max-w-xl surface-panel overflow-hidden shadow-lg">
        <div className="flex items-center gap-2.5 border-b border-[var(--border-hairline)] px-3.5 py-2.5">
          <Search className="h-4 w-4 text-[var(--text-muted)] shrink-0" />
          <input
            autoFocus
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIdx(0);
            }}
            placeholder="Cerca sezione, ricerca salvata o export..."
            className="w-full bg-transparent text-[13px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none"
          />
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 text-[var(--text-muted)] hover:bg-[var(--bg-subtle)]"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="max-h-[360px] overflow-y-auto divide-y divide-[var(--border-hairline)]">
          {filtered.length === 0 ? (
            <div className="py-10 text-center text-[13px] text-[var(--text-muted)]">
              Nessun risultato per &ldquo;{query}&rdquo;
            </div>
          ) : (
            filtered.map((item, idx) => {
              const active = idx === selectedIdx;
              return (
                <button
                  key={item.id}
                  type="button"
                  onMouseEnter={() => setSelectedIdx(idx)}
                  onClick={() => {
                    router.push(item.href);
                    onClose();
                  }}
                  className={`flex w-full items-center justify-between gap-3 px-3.5 py-2.5 text-left transition-colors ${
                    active ? "bg-[var(--accent-tint)]" : "hover:bg-[var(--bg-subtle)]"
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    {item.icon}
                    <div className="min-w-0">
                      <div className="truncate text-[13px] font-medium text-[var(--text-primary)]">
                        {item.label}
                      </div>
                      <div className="truncate text-[11px] text-[var(--text-muted)]">
                        {item.group} · {item.subtitle}
                      </div>
                    </div>
                  </div>
                  <ArrowRight className="h-3.5 w-3.5 text-[var(--text-muted)] shrink-0" />
                </button>
              );
            })
          )}
        </div>

        <div className="flex items-center justify-between border-t border-[var(--border-hairline)] bg-[var(--bg-subtle)] px-3.5 py-1.5 text-[11px] text-[var(--text-muted)]">
          <span>Usa ↑ ↓ per spostarti · Invio per aprire</span>
          <span>ESC chiudi</span>
        </div>
      </div>
    </div>
  );
}
