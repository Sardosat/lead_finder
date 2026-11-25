"use client";

import React from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface FunnelStage {
  stage: string;
  count: number;
  pct: number;
}

const STAGE_COLORS = ["#1E293B", "#1D4ED8", "#2563EB", "#0F766E", "#059669"];

export function QualityFunnelChart({ data }: { data: FunnelStage[] }) {
  return (
    <div className="surface-panel p-4 min-w-0">
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <div>
          <h2 className="text-[13px] font-semibold text-[var(--text-primary)]">
            Imbuto Qualità Dati &amp; Conformità
          </h2>
          <p className="text-[12px] text-[var(--text-muted)]">
            Conteggio reale progressivo da anagrafica grezza fino a contatti pronti GDPR LIA Pass
          </p>
        </div>
      </div>

      <div className="h-[250px] w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 64, left: 10, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" horizontal={false} />
            <XAxis type="number" hide />
            <YAxis
              type="category"
              dataKey="stage"
              width={190}
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
              formatter={(value: number, _name: string, item: { payload?: FunnelStage }) => [
                `${value.toLocaleString("it-IT")} (${item?.payload?.pct ?? 0}%)`,
                "Aziende",
              ]}
            />
            <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={24}>
              {data.map((entry, idx) => (
                <Cell key={entry.stage} fill={STAGE_COLORS[idx % STAGE_COLORS.length]} />
              ))}
              <LabelList
                dataKey="pct"
                position="right"
                formatter={(v: number) => `${v}%`}
                style={{ fontSize: 11, fontWeight: 600, fill: "#334155" }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
