// frontend/app/page.tsx
"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { AuthGate } from "@/components/AuthGate";
import { ChatPanel } from "@/components/ChatPanel";
import { ReasoningTrace } from "@/components/ReasoningTrace";
import { streamChat, fetchHistory, subscribeToAlerts } from "@/lib/chatClient";
import { isPushSupported, subscribeToPush } from "@/lib/push";
import { AuthResponse, ChatMessage, ProactiveAlert, RouteWaypoint, TraceEntry } from "@/lib/types";

const MapView = dynamic(() => import("@/components/MapView").then((m) => m.MapView), { ssr: false });

const AUTH_STORAGE_KEY = "orca-auth";

function loadStoredAuth(): AuthResponse | null {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function storeAuth(auth: AuthResponse | null) {
  try {
    if (auth) localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(auth));
    else localStorage.removeItem(AUTH_STORAGE_KEY);
  } catch {
    // best-effort persistence only
  }
}

function getOrCreateSessionId(email: string | null): string {
  const key = `orca-session-id:${email ?? "guest"}`;
  try {
    const existing = localStorage.getItem(key);
    if (existing) return existing;
  } catch {
    // localStorage unavailable (private browsing, etc.) -- fall through to a fresh id
  }
  const id = crypto.randomUUID();
  try {
    localStorage.setItem(key, id);
  } catch {
    // best-effort persistence only
  }
  return id;
}

export default function Home() {
  const [auth, setAuth] = useState<AuthResponse | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [showAuthGate, setShowAuthGate] = useState(false);

  useEffect(() => {
    setAuth(loadStoredAuth());
    setAuthChecked(true);
  }, []);

  if (!authChecked) return null;

  if (showAuthGate) {
    return (
      <AuthGate
        onAuthenticated={(a) => {
          storeAuth(a);
          setAuth(a);
          setShowAuthGate(false);
        }}
        onSkip={() => setShowAuthGate(false)}
      />
    );
  }

  return (
    <ChatApp
      auth={auth}
      onLogin={() => setShowAuthGate(true)}
      onLogout={() => {
        storeAuth(null);
        setAuth(null);
      }}
    />
  );
}

function ChatApp({
  auth,
  onLogin,
  onLogout,
}: {
  auth: AuthResponse | null;
  onLogin: () => void;
  onLogout: () => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [resolvedPlaceName, setResolvedPlaceName] = useState<string | null>(null);
  const [route, setRoute] = useState<RouteWaypoint[] | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId] = useState(() => getOrCreateSessionId(auth?.email ?? null));
  const [activeAlert, setActiveAlert] = useState<ProactiveAlert | null>(null);
  const [pushStatus, setPushStatus] = useState<"idle" | "subscribing" | "subscribed" | "error">("idle");

  async function handleEnablePush() {
    setPushStatus("subscribing");
    try {
      await subscribeToPush(sessionId, auth?.token);
      setPushStatus("subscribed");
    } catch {
      setPushStatus("error");
    }
  }

  useEffect(() => {
    fetchHistory(sessionId, auth?.token)
      .then((history) => {
        setMessages(history);
        // If history has location, recover it
        const lastWithLoc = [...history].reverse().find((m) => m.location);
        if (lastWithLoc?.location) {
          const lat = lastWithLoc.location.latitude ?? lastWithLoc.location.lat;
          const lon = lastWithLoc.location.longitude ?? lastWithLoc.location.lon;
          if (typeof lat === "number" && typeof lon === "number") {
            setLocation({ lat, lon });
            setResolvedPlaceName(lastWithLoc.location.display_name || lastWithLoc.location.district || null);
          }
        }
      })
      .catch(() => {
        // No persisted history yet, or the backend is unreachable -- start fresh.
      });
  }, [sessionId, auth?.token]);

  useEffect(() => {
    return subscribeToAlerts(sessionId, auth?.token, setActiveAlert);
  }, [sessionId, auth?.token]);

  async function handleSend(message: string) {
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setTrace([]);
    setRoute(null);
    setIsStreaming(true);
    try {
      for await (const event of streamChat(sessionId, message, auth?.token, location)) {
        if (event.type === "trace") {
          setTrace((prev) => [...prev, event.data]);
          if (event.data.agent === "geospatial") {
            const out = event.data.output as { lat?: number; lon?: number; resolved_name?: string; nearest_coastal_name?: string };
            if (typeof out.lat === "number" && typeof out.lon === "number") {
              setLocation({ lat: out.lat, lon: out.lon });
              if (out.resolved_name) setResolvedPlaceName(out.resolved_name);
              else if (out.nearest_coastal_name) setResolvedPlaceName(out.nearest_coastal_name);
            }
          } else if (event.data.agent === "route") {
            const waypoints = event.data.output["waypoints"] as RouteWaypoint[] | undefined;
            if (waypoints) setRoute(waypoints);
          }
        } else if (event.type === "answer") {
          const loc = event.data.location;
          let newPlaceName = resolvedPlaceName;
          if (loc && (loc.latitude != null || loc.lat != null)) {
            const lat = loc.latitude ?? loc.lat!;
            const lon = loc.longitude ?? loc.lon!;
            setLocation({ lat, lon });
            newPlaceName = loc.display_name || loc.district || loc.nearest_coastal_name || newPlaceName;
            setResolvedPlaceName(newPlaceName);
          } else if (event.data.evidence && event.data.evidence.length > 0) {
            const firstWithCoords = event.data.evidence.find(
              (p) => typeof p.latitude === "number" && typeof p.longitude === "number"
            );
            if (firstWithCoords) {
              setLocation({ lat: firstWithCoords.latitude, lon: firstWithCoords.longitude });
            }
          }

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
              message_type: event.data.risk ? "answer" : undefined,
            },
          ]);
        }
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Unable to complete marine telemetry analysis. Could not connect to INCOIS/IMD feeds or the requested coastal coordinates could not be resolved. Please try again or specify a port name.",
          is_error: true,
          message_type: "error",
        },
      ]);
    } finally {
      setIsStreaming(false);
    }
  }

  // Build high-context map label
  const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant" && m.risk);
  const mapLabel = location
    ? `${resolvedPlaceName ? `${resolvedPlaceName} · ` : ""}Sector (${location.lat.toFixed(2)}°N, ${location.lon.toFixed(2)}°E)${
        lastAssistantMsg?.risk ? ` — Risk: ${lastAssistantMsg.risk.risk_level} (${lastAssistantMsg.risk.risk_score}/100)` : ""
      }`
    : undefined;

  return (
    <main className="flex flex-col h-screen bg-slate-100/70 text-slate-900 font-sans overflow-hidden">
      {/* ── TOP PLATFORM NAVIGATION & STATUS BAR (Clean Apple HIG Design) ── */}
      <header className="sticky top-0 z-30 px-4 sm:px-6 py-2.5 bg-white/90 backdrop-blur-md border-b border-slate-200/80 shadow-[0_1px_4px_rgba(0,0,0,0.03)] shrink-0 flex flex-wrap items-center justify-between gap-3">
        {/* Left Section: Branding & User Session Group */}
        <div className="flex items-center gap-3.5 min-w-0">
          {/* Brand Mark */}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-black text-white flex items-center justify-center text-sm font-black shadow-xs ring-1 ring-black/10">
              🌊
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-base tracking-tight text-slate-900">
                  ORCA
                </span>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200/80">
                  SIH26176
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-medium hidden md:block leading-none mt-0.5">
                Marine Ecosystem Reasoning with Collaborative Agents
              </p>
            </div>
          </div>

          <div className="h-4 w-px bg-slate-200 hidden sm:block" />

          {/* User Account / Session Pill */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200/90 text-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            <span className="font-mono text-slate-700 text-[11px] truncate max-w-[140px] sm:max-w-[180px]">
              {auth?.email ?? "Guest Session"}
            </span>
            {auth ? (
              <button
                onClick={onLogout}
                className="ml-1 text-[11px] font-semibold text-slate-500 hover:text-black transition-colors"
              >
                Log out
              </button>
            ) : (
              <button
                onClick={onLogin}
                className="ml-1 text-[11px] font-semibold text-slate-900 hover:text-black underline underline-offset-2 transition-colors"
              >
                Log in
              </button>
            )}
          </div>
        </div>

        {/* Center Section: Hazard Push Alert Control */}
        <div className="flex items-center">
          {isPushSupported() && (
            <div className="flex items-center">
              {pushStatus === "subscribed" ? (
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span>Hazard Alerts Active</span>
                </div>
              ) : (
                <button
                  onClick={handleEnablePush}
                  disabled={pushStatus === "subscribing"}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 hover:bg-black text-slate-700 hover:text-white border border-slate-200 text-xs font-medium transition-all shadow-2xs disabled:opacity-50"
                  aria-label="Enable hazard push notifications"
                >
                  <span>🔔</span>
                  <span>
                    {pushStatus === "subscribing"
                      ? "Enabling..."
                      : pushStatus === "error"
                      ? "Alerts failed · Retry?"
                      : "Enable Hazard Alerts"}
                  </span>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Right Section: Telemetry & Data Source Feeds */}
        <div className="flex items-center gap-2 text-[11px]">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 hidden xl:inline-block mr-1">
            Telemetry Feeds:
          </span>
          {/* INCOIS */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200/90 shadow-2xs">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
            <span className="font-semibold text-slate-900">INCOIS</span>
            <span className="text-slate-400 font-mono text-[10px]">OSF & PFZ</span>
          </div>

          {/* IMD */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200/90 shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-sky-500" />
            <span className="font-semibold text-slate-900">IMD</span>
            <span className="text-slate-400 font-mono text-[10px]">ADVISORY</span>
          </div>

          {/* ISRO */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-50 border border-slate-200/90 shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-indigo-500" />
            <span className="font-semibold text-slate-900">ISRO</span>
            <span className="text-slate-400 font-mono text-[10px]">SATELLITE</span>
          </div>
        </div>
      </header>

      {/* ── ACTIVE HAZARD ALERT BANNER ── */}
      {activeAlert && (
        <div className="bg-amber-50 border-b border-amber-200 text-amber-950 px-4 py-2.5 flex items-center justify-between gap-4 shrink-0 text-xs sm:text-sm animate-in fade-in slide-in-from-top-1 duration-200">
          <div className="flex items-center gap-2">
            <span className="text-base">⚠️</span>
            <span>
              <strong>Hazard Alert:</strong> Sector conditions turned{" "}
              <span className="font-bold uppercase underline">{activeAlert.verdict}</span> —{" "}
              {activeAlert.reasons.join("; ")}
            </span>
          </div>
          <button
            onClick={() => setActiveAlert(null)}
            className="text-xs font-semibold px-2.5 py-1 rounded-full bg-amber-100 hover:bg-amber-200 text-amber-900 transition-colors"
            aria-label="Dismiss alert"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── MAIN RESPONSIVE SPLIT WORKSPACE ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 flex-1 min-h-0 overflow-hidden">
        {/* Left Panel: Conversational Intelligence & Recommendations (7 cols) */}
        <div className="lg:col-span-7 h-full border-r border-slate-200/80 flex flex-col min-h-0 bg-slate-50/50">
          <ChatPanel
            messages={messages}
            onSend={handleSend}
            isStreaming={isStreaming}
            currentTrace={trace}
          />
        </div>

        {/* Right Panel: Spatial Map (50%) + Reasoning Pipeline Trace (50%) (5 cols) */}
        <div className="lg:col-span-5 h-full flex flex-col min-h-0 bg-white">
          {/* Top Half: Ocean Map & Marine Sectors */}
          <div className="h-1/2 border-b border-slate-200 relative flex flex-col min-h-0">
            <div className="px-3.5 py-2 bg-white/95 backdrop-blur-md border-b border-slate-200/90 flex items-center justify-between text-xs z-10 shadow-2xs">
              <div className="flex items-center gap-2">
                <span className="text-sm">🗺️</span>
                <span className="font-bold text-slate-800 tracking-tight">
                  Ocean Map & Marine Sectors
                </span>
              </div>
              {location && (
                <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200/80 font-mono text-[11px] text-slate-700">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  <span>
                    {location.lat.toFixed(2)}°N, {location.lon.toFixed(2)}°E
                  </span>
                </div>
              )}
            </div>

            <div className="flex-1 relative min-h-0">
              <MapView
                lat={location?.lat ?? null}
                lon={location?.lon ?? null}
                label={mapLabel}
                route={route ?? undefined}
                placeName={resolvedPlaceName}
              />
            </div>
          </div>

          {/* Bottom Half: Multi-Agent Reasoning Trace */}
          <div className="h-1/2 flex flex-col min-h-0">
            <ReasoningTrace trace={trace} isStreaming={isStreaming} />
          </div>
        </div>
      </div>
    </main>
  );
}
