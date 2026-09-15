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
    return <p className="p-4 text-sm text-slate-500">No reasoning steps yet.</p>;
  }
  return (
    <ul className="p-4 space-y-3 overflow-y-auto h-full">
      {trace.map((entry, i) => {
        const trend = entry.output["sst_trend_celsius"];
        return (
          <li key={i} className="border rounded p-2 text-sm">
            <div className="font-semibold">{entry.agent}</div>
            <div className="text-slate-600">sources: {entry.sources.join(", ")}</div>
            {entry.is_cached && (
              <div className="text-amber-600">cached data from {entry.fetched_at ?? "unknown time"}</div>
            )}
            {entry.output["geofence_warning"] != null && (
              <div className="text-amber-700 dark:text-amber-400 font-medium">
                {String(entry.output["geofence_warning"])}
              </div>
            )}
            {isTrendPointArray(trend) && <SstTrendChart trend={trend} />}
            <pre className="whitespace-pre-wrap text-xs mt-1">{JSON.stringify(entry.output, null, 2)}</pre>
          </li>
        );
      })}
    </ul>
  );
}
