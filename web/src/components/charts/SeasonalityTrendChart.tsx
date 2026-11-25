"use client";

import React from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface SeasonalityPoint {
  month: string;
  climatizzazione: number;
  caldaie_termoidraulica: number;
  manutenzione_pdc: number;
}

export function SeasonalityTrendChart({ data }: { data: SeasonalityPoint[] }) {
  return (
    <div className="surface-panel p-4 min-w-0">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
              Curva Domanda Stagionale 12 Mesi — Area Etnea &amp; Sicilia
            </h2>
            <span className="rounded border border-amber-200 bg-amber-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-800">
              Stima Teorica
            </span>
          </div>
          <p className="text-[12px] text-[var(--text-muted)]">
            Indice operativo (0–100) per pianificare campagne outbound prima dei picchi caldo/freddo
          </p>
        </div>
      </div>

      <div className="h-[265px] w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 20, left: -12, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 11, fill: "#475569" }}
              axisLine={{ stroke: "#E5E7EB" }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fontSize: 11, fill: "#64748B" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                fontSize: "12px",
                borderRadius: "6px",
                border: "1px solid #E5E7EB",
                backgroundColor: "#FFFFFF",
              }}
            />
            <Legend wrapperStyle={{ fontSize: "11px" }} />
            <Line
              type="monotone"
              dataKey="climatizzazione"
              name="Climatizzazione & HVAC"
              stroke="#D97706"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
            <Line
              type="monotone"
              dataKey="caldaie_termoidraulica"
              name="Caldaie & Termoidraulica"
              stroke="#1D4ED8"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
            <Line
              type="monotone"
              dataKey="manutenzione_pdc"
              name="Manutenzioni Programmate & PdC"
              stroke="#059669"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
