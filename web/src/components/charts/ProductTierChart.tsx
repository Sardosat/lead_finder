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

interface ProductTierRow {
  product_key: string;
  product_name: string;
  tier_a: number;
  tier_b: number;
  tier_c: number;
  total: number;
}

export function ProductTierChart({ data }: { data: ProductTierRow[] }) {
  return (
    <div className="surface-panel p-4 min-w-0">
      <div className="mb-3">
        <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
          Routing Ecosistema Prodotti × Tier ICP
        </h2>
        <p className="text-[12px] text-[var(--text-muted)]">
          Smistamento automatico su TecnicoLIVE, RSK System e MonetizeLab suddiviso per priorità commerciale
        </p>
      </div>

      <div className="h-[250px] w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 16, left: -12, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
            <XAxis
              dataKey="product_name"
              tick={{ fontSize: 11, fill: "#475569" }}
              axisLine={{ stroke: "#E5E7EB" }}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#64748B" }}
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
            <Bar dataKey="tier_a" name="Tier A (Hot)" stackId="tier" fill="#059669" radius={[0, 0, 0, 0]} barSize={44} />
            <Bar dataKey="tier_b" name="Tier B (Warm)" stackId="tier" fill="#D97706" radius={[0, 0, 0, 0]} barSize={44} />
            <Bar dataKey="tier_c" name="Tier C (Da arricchire)" stackId="tier" fill="#94A3B8" radius={[4, 4, 0, 0]} barSize={44} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
