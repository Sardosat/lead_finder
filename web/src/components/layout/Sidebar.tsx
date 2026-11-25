"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Archive,
  FolderSearch,
  LayoutDashboard,
  LogOut,
  MessageSquareText,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Settings,
  ShieldCheck,
  Sun,
  TableProperties,
  TrendingUp,
  X,
  Zap,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

export const NAV_GROUPS: Array<{ title: string; items: NavItem[] }> = [
  {
    title: "Scoperta",
    items: [
      { label: "Panoramica", href: "/", icon: LayoutDashboard },
      { label: "Le mie Ricerche", href: "/ricerche", icon: FolderSearch },
      { label: "Lead Finder", href: "/leads", icon: TableProperties },
    ],
  },
  {
    title: "Mercato & Vendita",
    items: [
      { label: "Social & Market Radar", href: "/trends", icon: TrendingUp },
      { label: "Sales Hub & Bozze", href: "/outreach", icon: MessageSquareText },
      { label: "Archivio Export", href: "/exports", icon: Archive },
    ],
  },
  {
    title: "Sistema",
    items: [
      { label: "GDPR & Blacklist", href: "/compliance", icon: ShieldCheck },
      { label: "Impostazioni", href: "/impostazioni", icon: Settings },
    ],
  },
];

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  username: string;
  darkMode: boolean;
  onToggleTheme: () => void;
  onLogout: () => void;
}

export function Sidebar({
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
  username,
  darkMode,
  onToggleTheme,
  onLogout,
}: SidebarProps) {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const renderContent = (isMobile = false) => {
    const isRail = collapsed && !isMobile;
    return (
      <div className="flex h-full flex-col bg-[var(--bg-surface)] border-r border-[var(--border-hairline)] select-none">
        {/* Header Brand + Toggle */}
        <div
          className={`flex h-[52px] items-center border-b border-[var(--border-hairline)] px-3 ${
            isRail ? "justify-center" : "justify-between"
          }`}
        >
          {!isRail && (
            <Link href="/" className="flex items-center gap-2.5 min-w-0" onClick={onCloseMobile}>
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-[#1D4ED8] text-white">
                <Zap className="h-4 w-4" />
              </span>
              <div className="min-w-0 leading-tight">
                <div className="truncate text-[13px] font-semibold tracking-tight text-[var(--text-primary)]">
                  Lead Engine
                </div>
                <div className="truncate text-[11px] text-[var(--text-muted)]">IT/EU Intelligence</div>
              </div>
            </Link>
          )}
          {isRail && (
            <button
              type="button"
              onClick={onToggleCollapse}
              title="Espandi sidebar (⌘B)"
              className="flex h-8 w-8 items-center justify-center rounded-md text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] transition-colors"
            >
              <PanelLeftOpen className="h-4 w-4" />
            </button>
          )}
          {!isRail && !isMobile && (
            <button
              type="button"
              onClick={onToggleCollapse}
              title="Comprimi sidebar (⌘B)"
              aria-label="Comprimi sidebar"
              className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--text-muted)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] transition-colors"
            >
              <PanelLeftClose className="h-4 w-4" />
            </button>
          )}
          {isMobile && (
            <button
              type="button"
              onClick={onCloseMobile}
              aria-label="Chiudi menu"
              className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--text-muted)] hover:bg-[var(--bg-subtle)]"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Primary CTA */}
        <div className="px-3 pt-3 pb-2">
          <Link
            href="/ricerca/nuova"
            onClick={onCloseMobile}
            title={isRail ? "Nuova Ricerca" : undefined}
            className={`flex items-center justify-center gap-2 rounded-md bg-[#1D4ED8] hover:bg-[#1E40AF] text-white text-[13px] font-medium transition-colors ${
              isRail ? "h-9 w-9 mx-auto" : "h-9 px-3 w-full"
            }`}
          >
            <Plus className="h-4 w-4 shrink-0" />
            {!isRail && <span>Nuova Ricerca</span>}
          </Link>
        </div>

        {/* Navigation Groups */}
        <nav className="flex-1 overflow-y-auto px-2.5 py-2 space-y-5">
          {NAV_GROUPS.map((group) => (
            <div key={group.title}>
              {!isRail ? (
                <div className="px-2 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-[var(--text-muted)]">
                  {group.title}
                </div>
              ) : (
                <div className="mx-2 my-2 border-t border-[var(--border-hairline)]" />
              )}
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const active = isActive(item.href);
                  return (
                    <li key={item.href}>
                      <Link
                        href={item.href}
                        onClick={onCloseMobile}
                        title={isRail ? item.label : undefined}
                        className={`group flex items-center gap-2.5 rounded-md text-[13px] transition-colors ${
                          isRail ? "h-9 w-9 justify-center mx-auto" : "h-8 px-2.5"
                        } ${
                          active
                            ? "bg-[var(--accent-tint)] text-[var(--accent)] font-medium"
                            : "text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]"
                        }`}
                      >
                        <Icon
                          className={`h-4 w-4 shrink-0 ${
                            active
                              ? "text-[var(--accent)]"
                              : "text-[var(--text-muted)] group-hover:text-[var(--text-primary)]"
                          }`}
                        />
                        {!isRail && <span className="truncate">{item.label}</span>}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        {/* Footer Controls */}
        <div className="border-t border-[var(--border-hairline)] p-2.5 space-y-1">
          <button
            type="button"
            onClick={onToggleTheme}
            title={darkMode ? "Passa a Light Theme" : "Passa a Dark Theme"}
            className={`flex items-center gap-2.5 rounded-md text-[12px] text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] transition-colors ${
              isRail ? "h-8 w-8 justify-center mx-auto" : "h-8 px-2.5 w-full"
            }`}
          >
            {darkMode ? <Sun className="h-4 w-4 shrink-0" /> : <Moon className="h-4 w-4 shrink-0" />}
            {!isRail && <span>{darkMode ? "Tema Chiaro" : "Tema Scuro"}</span>}
          </button>

          <div
            className={`flex items-center ${
              isRail ? "justify-center pt-1" : "justify-between px-2.5 pt-1"
            }`}
          >
            {!isRail && (
              <div className="min-w-0">
                <div className="truncate text-[12px] font-medium text-[var(--text-primary)]">
                  {username || "admin"}
                </div>
                <div className="text-[11px] text-[var(--text-muted)]">Sessione attiva</div>
              </div>
            )}
            <button
              type="button"
              onClick={onLogout}
              title="Esci dall'account"
              aria-label="Esci"
              className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--text-muted)] hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-950/40 dark:hover:text-red-300 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Desktop Sidebar */}
      <aside
        className={`hidden lg:block shrink-0 transition-[width] duration-200 ease-out ${
          collapsed ? "w-[60px]" : "w-[240px]"
        }`}
      >
        <div className="sticky top-0 h-screen">{renderContent(false)}</div>
      </aside>

      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="fixed inset-0 bg-slate-900/35" onClick={onCloseMobile} />
          <aside className="relative z-10 w-[260px] h-full">{renderContent(true)}</aside>
        </div>
      )}
    </>
  );
}
