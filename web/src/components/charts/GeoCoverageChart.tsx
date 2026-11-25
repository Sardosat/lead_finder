"use client";

import React, { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface CoverageRow {
  label: string;
  total: number;
  callable: number;
  to_enrich: number;
}

export function GeoCoverageChart({
  geoData,
  nicheData,
}: {
  geoData: CoverageRow[];
  nicheData: CoverageRow[];
}) {
  const [mode, setMode] = useState<"geo" | "niche">("geo");
  const activeData = mode === "geo" ? geoData : nicheData;

  return (
    <div className="surface-panel p-4 min-w-0">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
            Copertura Territoriale &amp; Nicchie Operative
          </h2>
          <p className="text-[12px] text-[var(--text-muted)]">
            Confronto diretto tra aziende chiamabili subito (E.164) e aziende prive di telefono da arricchire
          </p>
        </div>

        <div className="inline-flex rounded-md border border-[var(--border-hairline)] bg-[var(--bg-subtle)] p-0.5 text-[12px]">
          <button
            type="button"
            onClick={() => setMode("geo")}
            className={`rounded px-2.5 py-1 font-medium transition-colors ${
              mode === "geo"
                ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            }`}
          >
            Per Comune
          </button>
          <button
            type="button"
            onClick={() => setMode("niche")}
            className={`rounded px-2.5 py-1 font-medium transition-colors ${
              mode === "niche"
                ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-xs"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            }`}
          >
            Per Nicchia
          </button>
        </div>
      </div>

      <div className="h-[270px] w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={activeData} layout="vertical" margin={{ top: 4, right: 20, left: 10, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey="label"
              width={165}
              tick={{ fontSize: 11, fill: "#475569" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ fill: "#F8FAFC" }}
              contentStyle={{
                fontSize: "12px",
                borderRadius: "6px",
                border: "1px solid #E5E7EB",
                backgroundColor: "#FFFFFF",
              }}
            />
            <Legend wrapperStyle={{ fontSize: "11px" }} />
            <Bar dataKey="callable" name="Chiamabili E.164" stackId="cov" fill="#1D4ED8" barSize={16} />
            <Bar
              dataKey="to_enrich"
              name="Senza Telefono (Da Arricchire)"
              stackId="cov"
              fill="#CBD5E1"
              radius={[0, 4, 4, 0]}
              barSize={16}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
