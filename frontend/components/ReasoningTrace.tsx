// frontend/components/ReasoningTrace.tsx
import { TraceEntry } from "@/lib/types";

export function ReasoningTrace({ trace }: { trace: TraceEntry[] }) {
  if (trace.length === 0) {
    return <p className="p-4 text-sm text-slate-500">No reasoning steps yet.</p>;
  }
  return (
    <ul className="p-4 space-y-3 overflow-y-auto h-full">
      {trace.map((entry, i) => (
        <li key={i} className="border rounded p-2 text-sm">
          <div className="font-semibold">{entry.agent}</div>
          <div className="text-slate-600">sources: {entry.sources.join(", ")}</div>
          {entry.is_cached && (
            <div className="text-amber-600">cached data from {entry.fetched_at ?? "unknown time"}</div>
          )}
          <pre className="whitespace-pre-wrap text-xs mt-1">{JSON.stringify(entry.output, null, 2)}</pre>
        </li>
      ))}
    </ul>
  );
}
