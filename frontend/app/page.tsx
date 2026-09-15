// frontend/app/page.tsx
"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { ChatPanel } from "@/components/ChatPanel";
import { ReasoningTrace } from "@/components/ReasoningTrace";
import { streamChat, fetchHistory, subscribeToAlerts } from "@/lib/chatClient";
import { ChatMessage, ProactiveAlert, RouteWaypoint, TraceEntry } from "@/lib/types";

const MapView = dynamic(() => import("@/components/MapView").then((m) => m.MapView), { ssr: false });

const SESSION_STORAGE_KEY = "orca-session-id";

function getOrCreateSessionId(): string {
  try {
    const existing = localStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) return existing;
  } catch {
    // localStorage unavailable (private browsing, etc.) -- fall through to a fresh id
  }
  const id = crypto.randomUUID();
  try {
    localStorage.setItem(SESSION_STORAGE_KEY, id);
  } catch {
    // best-effort persistence only
  }
  return id;
}

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [route, setRoute] = useState<RouteWaypoint[] | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId] = useState(getOrCreateSessionId);
  const [activeAlert, setActiveAlert] = useState<ProactiveAlert | null>(null);

  useEffect(() => {
    fetchHistory(sessionId)
      .then(setMessages)
      .catch(() => {
        // No persisted history yet, or the backend is unreachable -- start fresh.
      });
  }, [sessionId]);

  useEffect(() => {
    return subscribeToAlerts(sessionId, setActiveAlert);
  }, [sessionId]);

  async function handleSend(message: string) {
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setTrace([]);
    setRoute(null);
    setIsStreaming(true);
    try {
      for await (const event of streamChat(sessionId, message, location)) {
        if (event.type === "trace") {
          setTrace((prev) => [...prev, event.data]);
          if (event.data.agent === "geospatial") {
            const { lat, lon } = event.data.output as { lat: number; lon: number };
            if (typeof lat === "number" && typeof lon === "number") setLocation({ lat, lon });
          } else if (event.data.agent === "route") {
            const waypoints = event.data.output["waypoints"] as RouteWaypoint[] | undefined;
            if (waypoints) setRoute(waypoints);
          }
        } else if (event.type === "answer") {
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: event.data.answer,
              risk: event.data.risk,
              verification: event.data.verification,
              what_if: event.data.what_if,
              evidence: event.data.evidence,
              location: event.data.location,
            },
          ]);
          if (
            event.data.location &&
            (event.data.location.latitude != null || event.data.location.lat != null)
          ) {
            const lat = event.data.location.latitude ?? event.data.location.lat!;
            const lon = event.data.location.longitude ?? event.data.location.lon!;
            setLocation({ lat, lon });
          } else if (event.data.evidence && event.data.evidence.length > 0) {
            const firstWithCoords = event.data.evidence.find(
              (p) => typeof p.latitude === "number" && typeof p.longitude === "number"
            );
            if (firstWithCoords) {
              setLocation({ lat: firstWithCoords.latitude, lon: firstWithCoords.longitude });
            }
          }
        }
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong while processing your request. Please try again." },
      ]);
    } finally {
      setIsStreaming(false);
    }
  }

  // Get current risk level for map label if available from the last message
  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant" && m.risk);
  const mapLabel = location
    ? `Coastal Sector (${location.lat.toFixed(2)}°N, ${location.lon.toFixed(2)}°E)${
        lastAssistantMsg?.risk ? ` — Risk: ${lastAssistantMsg.risk.risk_level} (${lastAssistantMsg.risk.risk_score}/100)` : ""
      }`
    : undefined;

  return (
    <main className="flex flex-col h-screen bg-slate-50">
      {/* Platform Header */}
      <header className="px-5 py-3 bg-white border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 shadow-xs shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-black text-white font-black flex items-center justify-center text-sm shadow-xs">
            🌊
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-base tracking-tight text-black">
                ORCA
              </span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-800 border border-slate-200">
                SIH26176 • Alt F4
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              Marine EcOsystem Reasoning with Collaborative Agents
            </p>
          </div>
        </div>

        {/* Data Source Status Badges (Monochrome Apple Style) */}
        <div className="flex items-center gap-2 text-[11px]">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-black" />
            <span className="font-semibold text-slate-800">INCOIS:</span>
            <span className="text-slate-500 font-mono text-[10px]">FORECAST</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-600" />
            <span className="font-semibold text-slate-800">IMD:</span>
            <span className="text-slate-500 font-mono text-[10px]">VERIFIED</span>
          </div>
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            <span className="font-semibold text-slate-800">ISRO:</span>
            <span className="text-slate-500 font-mono text-[10px]">SATELLITE</span>
          </div>
        </div>
      </header>

      {/* Hazard Alert Banner (Monochrome Apple Style) */}
      {activeAlert && (
        <div className="bg-slate-100 border-b border-slate-300 text-slate-900 px-4 py-2 flex items-center justify-between gap-4 shrink-0 text-sm">
          <span>
            ⚠️ Hazard alert: conditions near your last query turned <strong>{activeAlert.verdict}</strong> —{" "}
            {activeAlert.reasons.join("; ")}
          </span>
          <button
            onClick={() => setActiveAlert(null)}
            className="text-black font-semibold shrink-0 hover:underline"
            aria-label="Dismiss alert"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Responsive Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 flex-1 min-h-0 overflow-hidden">
        {/* Left / Primary Panel: Chat, Hero, What-If, Evidence (7 cols / ~58%) */}
        <div className="lg:col-span-7 h-full border-r border-slate-200 dark:border-slate-800 flex flex-col min-h-0">
          <ChatPanel messages={messages} onSend={handleSend} isStreaming={isStreaming} />
        </div>

        {/* Right Panel: Map (Top 50%) and Reasoning Trace (Bottom 50%) (5 cols / ~42%) */}
        <div className="lg:col-span-5 h-full flex flex-col min-h-0 bg-white dark:bg-slate-900">
          {/* Top Half: Ocean Map */}
          <div className="h-1/2 border-b border-slate-200 dark:border-slate-800 relative flex flex-col">
            <div className="px-3 py-1.5 bg-white/90 dark:bg-slate-900/90 backdrop-blur-xs border-b border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs z-10">
              <span className="font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                <span>🗺️</span> Ocean Map & Marine Sectors
              </span>
              {location && (
                <span className="font-mono text-[11px] text-slate-500">
                  {location.lat.toFixed(4)}°N, {location.lon.toFixed(4)}°E
                </span>
              )}
            </div>
            <div className="flex-1 relative">
              <MapView
                lat={location?.lat ?? null}
                lon={location?.lon ?? null}
                label={mapLabel}
                route={route ?? undefined}
              />
            </div>
          </div>

          {/* Bottom Half: Multi-Agent Reasoning Trace */}
          <div className="h-1/2 flex flex-col min-h-0">
            <ReasoningTrace trace={trace} />
          </div>
        </div>
      </div>
    </main>
  );
}
