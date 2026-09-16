// frontend/components/ReasoningTrace.tsx
import { TraceEntry } from "@/lib/types";
import { SstTrendChart } from "@/components/SstTrendChart";

function isTrendPointArray(value: unknown): value is { date: string; sst_celsius: number }[] {
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

export function ReasoningTrace({ trace }: { trace: TraceEntry[] }) {
  if (trace.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center text-slate-400">
        <span className="text-2xl mb-2">🧠</span>
        <p className="text-sm font-medium">No active reasoning trace</p>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          Submit a query to observe collaborative multi-agent execution and evidence verification in real time.
        </p>
      </div>
    );
  }

  const agentBadgeColor: Record<string, string> = {
    planner: "bg-purple-100 text-purple-800 border-purple-200 dark:bg-purple-950 dark:text-purple-300",
    geospatial: "bg-emerald-100 text-emerald-800 border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300",
    weather: "bg-sky-100 text-sky-800 border-sky-200 dark:bg-sky-950 dark:text-sky-300",
    risk: "bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950 dark:text-amber-300",
    ocean_analytics: "bg-teal-100 text-teal-800 border-teal-200 dark:bg-teal-950 dark:text-teal-300",
    reporting: "bg-indigo-100 text-indigo-800 border-indigo-200 dark:bg-indigo-950 dark:text-indigo-300",
  };

  return (
    <div className="flex flex-col h-full bg-slate-50/40 dark:bg-slate-900/40">
      <div className="px-4 py-3 border-b bg-white dark:bg-slate-900 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-slate-800 dark:text-slate-100">Multi-Agent Trace</span>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 font-mono text-slate-600 dark:text-slate-300">
            {trace.length} steps
          </span>
        </div>
        <span className="text-[11px] text-slate-400 font-medium">LangGraph Orchestration</span>
      </div>

      <ul className="p-3 space-y-3 overflow-y-auto flex-1 text-xs">
        {trace.map((entry, i) => {
          const trend = entry.output["sst_trend_celsius"];
          const badgeClass = agentBadgeColor[entry.agent] || "bg-slate-100 text-slate-800 border-slate-200";
          return (
            <li
              key={i}
              className="border border-slate-200 dark:border-slate-800 rounded-xl p-3 bg-white dark:bg-slate-900 shadow-sm space-y-2"
            >
              <div className="flex items-center justify-between">
                <span className={`px-2 py-0.5 rounded-md font-semibold text-[11px] border uppercase tracking-wider ${badgeClass}`}>
                  {entry.agent}
                </span>
                <span className="text-[10px] text-slate-400 font-mono">Step #{i + 1}</span>
              </div>

              {entry.sources.length > 0 && (
                <div className="flex flex-wrap items-center gap-1 text-[11px]">
                  <span className="text-slate-500">Sources:</span>
                  {entry.sources.map((s, sIdx) => (
                    <span
                      key={sIdx}
                      className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-medium"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}

              {entry.is_cached && (
                <div className="flex items-center gap-1 text-[11px] text-amber-600 dark:text-amber-400 font-medium">
                  <span>⚡ Cached snapshot</span>
                  <span className="text-[10px] text-slate-400">({entry.fetched_at ?? "persisted"})</span>
                </div>
              )}

              {entry.output["geofence_warning"] != null && (
                <div className="p-2 rounded bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300 font-medium text-[11px]">
                  ⚠️ {String(entry.output["geofence_warning"])}
                </div>
              )}

              {entry.agent === "weather" && entry.output["tide_height_m"] != null && (
                <div className="p-2 rounded bg-sky-50 dark:bg-sky-950/50 border border-sky-200 dark:border-sky-800 text-sky-800 dark:text-sky-300 text-[11px] space-y-0.5">
                  <div className="font-semibold">🌊 Tide: {String(entry.output["tide_height_m"])}m now</div>
                  {(() => {
                    const high = entry.output["next_high_tide"] as { time: string; height_m: number } | null;
                    const low = entry.output["next_low_tide"] as { time: string; height_m: number } | null;
                    return (
                      <>
                        {high && (
                          <div>Next high: {high.height_m}m at {new Date(high.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
                        )}
                        {low && (
                          <div>Next low: {low.height_m}m at {new Date(low.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
                        )}
                      </>
                    );
                  })()}
                </div>
              )}

              {isTrendPointArray(trend) && (
                <div className="pt-1">
                  <SstTrendChart trend={trend} />
                </div>
              )}

              <details className="mt-1 group">
                <summary className="cursor-pointer text-[10px] font-semibold text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 select-none">
                  Inspect agent output ▾
                </summary>
                <pre className="mt-1.5 p-2 bg-slate-50 dark:bg-slate-950 rounded-lg text-[10px] font-mono text-slate-700 dark:text-slate-300 overflow-x-auto max-h-48 border border-slate-100 dark:border-slate-800">
                  {JSON.stringify(entry.output, null, 2)}
                </pre>
              </details>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
