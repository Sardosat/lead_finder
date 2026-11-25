"use client";

import React from "react";
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

interface BenchmarkRow {
  metric: string;
  clay: number;
  engine: number;
}

export function ClayBenchmarkChart({ data }: { data: BenchmarkRow[] }) {
  return (
    <div className="surface-panel p-4 min-w-0">
      <div className="mb-3">
        <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
          Benchmark Reale: Clay.com (esempio.csv) vs Nostro Lead Engine IT/EU
        </h2>
        <p className="text-[12px] text-[var(--text-muted)]">
          Metriche percentuali misurate sui file reali del workspace (zero dati simulati)
        </p>
      </div>

      <div className="h-[260px] w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 16, left: -12, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
            <XAxis
              dataKey="metric"
              tick={{ fontSize: 11, fill: "#475569" }}
              axisLine={{ stroke: "#E5E7EB" }}
              tickLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tickFormatter={(v: number) => `${v}%`}
              tick={{ fontSize: 11, fill: "#64748B" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              formatter={(v: number) => `${v}%`}
              contentStyle={{
                fontSize: "12px",
                borderRadius: "6px",
                border: "1px solid #E5E7EB",
                backgroundColor: "#FFFFFF",
              }}
            />
            <Legend wrapperStyle={{ fontSize: "11px" }} />
            <Bar dataKey="clay" name="Clay.com (esempio.csv)" fill="#94A3B8" radius={[4, 4, 0, 0]} barSize={28} />
            <Bar dataKey="engine" name="Nostro Engine IT/EU" fill="#1D4ED8" radius={[4, 4, 0, 0]} barSize={28} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
