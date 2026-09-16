// frontend/components/EvidencePanel.tsx
"use client";

import React from "react";
import { BarChart3, Check } from "lucide-react";
import { MarineParameter, VerificationResult } from "@/lib/types";

interface EvidencePanelProps {
  evidence: MarineParameter[];
  verification?: VerificationResult | null;
}

const PARAM_FORMAT_MAP: Record<string, string> = {
  significant_wave_height: "Significant Wave Height",
  wave_period: "Mean Wave Period",
  swell_height: "Swell Wave Height",
  swell_period: "Swell Peak Period",
  wind_speed: "Wind Speed (10m)",
  wind_direction: "Wind Direction",
  surface_current_speed: "Surface Current Velocity",
  surface_current_direction: "Surface Current Direction",
  sst: "Sea Surface Temperature",
  satellite_sst: "Satellite Blended SST",
  chlorophyll: "Chlorophyll-a Concentration",
  diffuse_attenuation_kd490: "Diffuse Attenuation (Kd490)",
  total_suspended_matter: "Total Suspended Matter",
  weather_warning_level: "Weather Warning Advisory",
  rainfall_forecast: "24h Rainfall Forecast",
  port_warning_signal: "Port Cautionary Signal",
};

export function EvidencePanel({ evidence, verification }: EvidencePanelProps) {
  if (!evidence || evidence.length === 0) {
    return (
      <div className="p-4 text-xs text-slate-500 italic">
        No structured marine evidence available for this turn.
      </div>
    );
  }

  const statusStyles: Record<string, string> = {
    LIVE: "bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-200 border-green-200",
    FORECAST: "bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-200 border-blue-200",
    CACHED: "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-200 border-amber-200",
    HISTORICAL: "bg-purple-100 text-purple-800 dark:bg-purple-900/50 dark:text-purple-200 border-purple-200",
  };

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 shadow-sm mb-4">
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-slate-100 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-slate-700 dark:text-slate-200" />
          <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100">
            Grounding Evidence & Observation Audit
          </h4>
        </div>
        <div className="text-xs text-slate-500 font-medium">
          {evidence.length} verified metrics |{" "}
          <span className="text-emerald-600 dark:text-emerald-400 font-semibold inline-flex items-center gap-1">
            {verification?.is_verified ? (
              <>
                Provenance Audited <Check className="w-3 h-3 text-emerald-600 inline" />
              </>
            ) : (
              "Baseline Grounded"
            )}
          </span>
        </div>
      </div>

      <div className="overflow-x-auto my-2">
        <table className="w-full text-xs text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
              <th className="py-2 px-2.5">Parameter</th>
              <th className="py-2 px-2.5">Observed Value</th>
              <th className="py-2 px-2.5">Source</th>
              <th className="py-2 px-2.5">Status</th>
              <th className="py-2 px-2.5">Valid Window</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {evidence.map((item, idx) => {
              const label = PARAM_FORMAT_MAP[item.parameter] || item.parameter;
              const valStr =
                typeof item.value === "number"
                  ? `${item.value.toFixed(1)} ${item.unit}`.trim()
                  : `${item.value} ${item.unit}`.trim();
              const badgeClass =
                statusStyles[item.data_status] || "bg-slate-100 text-slate-700 border-slate-200";

              return (
                <tr
                  key={idx}
                  className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors"
                >
                  <td className="py-2 px-2.5 font-medium text-slate-800 dark:text-slate-200">
                    {label}
                  </td>
                  <td className="py-2 px-2.5 font-mono font-bold text-slate-900 dark:text-slate-100">
                    {valStr}
                  </td>
                  <td className="py-2 px-2.5 text-slate-600 dark:text-slate-300 font-medium">
                    {item.source}
                  </td>
                  <td className="py-2 px-2.5">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${badgeClass}`}
                    >
                      {item.data_status}
                    </span>
                  </td>
                  <td className="py-2 px-2.5 text-[11px] font-mono text-slate-500">
                    {item.valid_from && item.valid_until
                      ? `${item.valid_from.substring(11, 16)} - ${item.valid_until.substring(11, 16)} UTC`
                      : item.timestamp
                        ? item.timestamp.substring(0, 16).replace("T", " ")
                        : "Current"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {verification?.checks_passed && verification.checks_passed.length > 0 && (
        <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 flex flex-wrap gap-2 text-[10px] text-slate-500">
          {verification.checks_passed.map((chk, i) => (
            <span key={i} className="inline-flex items-center gap-1 text-slate-600 dark:text-slate-400">
              <Check className="w-3 h-3 text-emerald-500 inline" /> {chk}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
