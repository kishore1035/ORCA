// frontend/components/ReasoningTrace.tsx
"use client";

import { useState } from "react";
import { TraceEntry } from "@/lib/types";
import { SstTrendChart } from "./SstTrendChart";

function isTrendPointArray(
  value: unknown
): value is { date: string; sst_celsius: number }[] {
  return (
    Array.isArray(value) &&
    value.every(
      (p) =>
        p &&
        typeof p === "object" &&
        typeof (p as Record<string, unknown>).date === "string" &&
        typeof (p as Record<string, unknown>).sst_celsius === "number"
    )
  );
}

const AGENT_CONFIG: Record<
  string,
  { name: string; icon: string; badge: string; dot: string; desc: string }
> = {
  planner: {
    name: "Planner",
    icon: "🧭",
    badge: "bg-purple-50 text-purple-900 border-purple-200",
    dot: "bg-purple-600",
    desc: "Goal & Intent Extraction",
  },
  geospatial: {
    name: "Geospatial",
    icon: "🗺️",
    badge: "bg-emerald-50 text-emerald-900 border-emerald-200",
    dot: "bg-emerald-600",
    desc: "Coastal Sector & Bathymetry",
  },
  weather: {
    name: "Weather",
    icon: "🌊",
    badge: "bg-sky-50 text-sky-900 border-sky-200",
    dot: "bg-sky-600",
    desc: "INCOIS Forecast & IMD Alerts",
  },
  risk: {
    name: "Risk Engine",
    icon: "⚖️",
    badge: "bg-amber-50 text-amber-900 border-amber-200",
    dot: "bg-amber-600",
    desc: "Weighted Marine Risk Scoring",
  },
  ocean_analytics: {
    name: "Ocean Analytics",
    icon: "🛰️",
    badge: "bg-teal-50 text-teal-900 border-teal-200",
    dot: "bg-teal-600",
    desc: "ISRO SST & Chlorophyll Audit",
  },
  reporting: {
    name: "Reporting",
    icon: "📝",
    badge: "bg-indigo-50 text-indigo-900 border-indigo-200",
    dot: "bg-indigo-600",
    desc: "Evidence Grounding & Synthesis",
  },
  route: {
    name: "Route Safety",
    icon: "🚢",
    badge: "bg-blue-50 text-blue-900 border-blue-200",
    dot: "bg-blue-600",
    desc: "Passage Waypoint Assessment",
  },
};

export function ReasoningTrace({
  trace,
  isStreaming = false,
}: {
  trace: TraceEntry[];
  isStreaming?: boolean;
}) {
  // Persistent expanded states per step index across streaming updates
  const [expandedMap, setExpandedMap] = useState<Record<string, boolean>>({});
  const [copiedStep, setCopiedStep] = useState<string | null>(null);

  function toggleStep(key: string) {
    setExpandedMap((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  }

  function handleCopyJSON(key: string, data: unknown) {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopiedStep(key);
    setTimeout(() => setCopiedStep(null), 1800);
  }

  if (trace.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center text-slate-500 bg-slate-50/50">
        <div className="w-12 h-12 rounded-2xl bg-white border border-slate-200 shadow-2xs flex items-center justify-center text-xl mb-3">
          🧠
        </div>
        <p className="text-sm font-bold text-slate-800">
          No Active Reasoning Trace
        </p>
        <p className="text-xs text-slate-500 mt-1 max-w-xs leading-relaxed">
          Submit a query to observe LangGraph collaborative multi-agent execution, sensor audits, and evidence correlation in real time.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-50/40">
      {/* ── TRACE PANEL HEADER ── */}
      <div className="px-4 py-2.5 bg-white border-b border-slate-200 flex items-center justify-between shrink-0 shadow-2xs">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-slate-900 tracking-tight">
            Multi-Agent Reasoning Trace
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 font-mono font-semibold text-slate-700">
            {trace.length} {trace.length === 1 ? "step" : "steps"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isStreaming && (
            <span className="inline-flex items-center gap-1.5 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span>Orchestrating</span>
            </span>
          )}
          <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">
            LangGraph DAG
          </span>
        </div>
      </div>

      {/* ── PIPELINE TIMELINE LIST (Sequential & Visual Flow) ── */}
      <div className="p-3 sm:p-4 overflow-y-auto flex-1 space-y-3.5 text-xs">
        {trace.map((entry, i) => {
          const stepKey = `step-${entry.agent}-${i}`;
          const isExpanded = !!expandedMap[stepKey];
          const isLast = i === trace.length - 1;
          const isActive = isStreaming && isLast;
          const trend = entry.output["sst_trend_celsius"];
          const conf = AGENT_CONFIG[entry.agent] || {
            name: entry.agent,
            icon: "🤖",
            badge: "bg-slate-100 text-slate-800 border-slate-200",
            dot: "bg-slate-600",
            desc: "Agent Processing",
          };

          return (
            <div key={stepKey} className="relative flex gap-3 group">
              {/* Pipeline Connecting Spine */}
              {!isLast && (
                <div
                  className="absolute left-[15px] top-[30px] bottom-[-16px] w-[2px] bg-slate-200 group-hover:bg-slate-300 transition-colors"
                  aria-hidden="true"
                />
              )}

              {/* Step Number & Node Indicator */}
              <div className="relative shrink-0 flex flex-col items-center">
                <div
                  className={`w-8 h-8 rounded-full border flex items-center justify-center font-mono text-[11px] font-bold shadow-2xs z-10 transition-all ${
                    isActive
                      ? "bg-black text-white border-black ring-4 ring-slate-200 scale-105"
                      : "bg-white text-slate-700 border-slate-300 group-hover:border-slate-400"
                  }`}
                >
                  {String(i + 1).padStart(2, "0")}
                </div>
              </div>

              {/* Step Card Content */}
              <div
                className={`flex-1 rounded-2xl p-3.5 bg-white border shadow-2xs transition-all space-y-2.5 ${
                  isActive
                    ? "border-black/60 ring-2 ring-black/5"
                    : "border-slate-200 hover:border-slate-300"
                }`}
              >
                {/* Agent Header */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg font-bold text-[11px] border uppercase tracking-wider ${conf.badge}`}
                    >
                      <span>{conf.icon}</span>
                      <span>{conf.name}</span>
                    </span>
                    <span className="text-[11px] text-slate-400 font-medium hidden sm:inline">
                      {conf.desc}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400">
                    Step #{i + 1}
                  </span>
                </div>

                {/* Data Sources */}
                {entry.sources && entry.sources.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                    <span className="text-slate-400 font-medium">Sources:</span>
                    {entry.sources.map((s, sIdx) => (
                      <span
                        key={sIdx}
                        className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium border border-slate-200/80 text-[10px]"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                )}

                {/* Cached Snapshot Indicator */}
                {entry.is_cached && (
                  <div className="flex items-center gap-1.5 text-[11px] text-amber-800 bg-amber-50 px-2 py-1 rounded-lg border border-amber-200 font-medium">
                    <span>⚡ Snapshot Fallback:</span>
                    <span className="text-[10px] text-amber-700 font-mono">
                      {entry.fetched_at ? new Date(entry.fetched_at).toLocaleTimeString() : "Verified committed cache"}
                    </span>
                  </div>
                )}

                {/* Geofence Callout */}
                {entry.output["geofence_warning"] != null && (
                  <div className="p-2.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 font-medium text-[11px] flex items-start gap-1.5">
                    <span>⚠️</span>
                    <span>{String(entry.output["geofence_warning"])}</span>
                  </div>
                )}

                {/* Tide Data Callout for Weather Agent */}
                {entry.agent === "weather" && entry.output["tide_height_m"] != null && (
                  <div className="p-2.5 rounded-xl bg-sky-50 border border-sky-200 text-sky-950 text-[11px] space-y-1">
                    <div className="font-bold flex items-center gap-1.5">
                      <span>🌊</span>
                      <span>Current Tide: {String(entry.output["tide_height_m"])}m</span>
                    </div>
                    {(() => {
                      const high = entry.output["next_high_tide"] as {
                        time: string;
                        height_m: number;
                      } | null;
                      const low = entry.output["next_low_tide"] as {
                        time: string;
                        height_m: number;
                      } | null;
                      return (
                        <div className="grid grid-cols-2 gap-2 pt-1 text-[10px] text-sky-800 font-medium">
                          {high && (
                            <div>
                              Next high: <strong>{high.height_m}m</strong> at{" "}
                              {new Date(high.time).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </div>
                          )}
                          {low && (
                            <div>
                              Next low: <strong>{low.height_m}m</strong> at{" "}
                              {new Date(low.time).toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                )}

                {/* SST Sparkline Chart */}
                {isTrendPointArray(trend) && (
                  <div className="pt-1.5">
                    <SstTrendChart trend={trend} />
                  </div>
                )}

                {/* ── CONTROLLED PERSISTENT INSPECTOR ── */}
                <div className="pt-1 border-t border-slate-100">
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => toggleStep(stepKey)}
                      className="text-[11px] font-semibold text-slate-600 hover:text-black flex items-center gap-1 select-none transition-colors"
                      aria-expanded={isExpanded}
                    >
                      <span className="text-[10px]">{isExpanded ? "▼" : "▶"}</span>
                      <span>Inspect Agent Output</span>
                    </button>

                    {isExpanded && (
                      <button
                        onClick={() => handleCopyJSON(stepKey, entry.output)}
                        className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                      >
                        {copiedStep === stepKey ? "✓ Copied" : "Copy JSON"}
                      </button>
                    )}
                  </div>

                  {isExpanded && (
                    <pre className="mt-2 p-2.5 bg-slate-900 text-slate-100 rounded-xl text-[10px] font-mono overflow-x-auto max-h-52 border border-slate-800 shadow-inner">
                      {JSON.stringify(entry.output, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
