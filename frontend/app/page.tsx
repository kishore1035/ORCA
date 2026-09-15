// frontend/app/page.tsx
"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { AuthGate } from "@/components/AuthGate";
import { ChatPanel } from "@/components/ChatPanel";
import { ReasoningTrace } from "@/components/ReasoningTrace";
import { streamChat, fetchHistory, subscribeToAlerts } from "@/lib/chatClient";
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

function getOrCreateSessionId(email: string): string {
  const key = `orca-session-id:${email}`;
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

  useEffect(() => {
    setAuth(loadStoredAuth());
    setAuthChecked(true);
  }, []);

  if (!authChecked) return null;
  if (!auth) {
    return (
      <AuthGate
        onAuthenticated={(a) => {
          storeAuth(a);
          setAuth(a);
        }}
      />
    );
  }
  return (
    <ChatApp
      auth={auth}
      onLogout={() => {
        storeAuth(null);
        setAuth(null);
      }}
    />
  );
}

function ChatApp({ auth, onLogout }: { auth: AuthResponse; onLogout: () => void }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [route, setRoute] = useState<RouteWaypoint[] | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId] = useState(() => getOrCreateSessionId(auth.email));
  const [activeAlert, setActiveAlert] = useState<ProactiveAlert | null>(null);

  useEffect(() => {
    fetchHistory(sessionId, auth.token)
      .then(setMessages)
      .catch(() => {
        // No persisted history yet, or the backend is unreachable -- start fresh.
      });
  }, [sessionId, auth.token]);

  useEffect(() => {
    return subscribeToAlerts(sessionId, auth.token, setActiveAlert);
  }, [sessionId, auth.token]);

  async function handleSend(message: string) {
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setTrace([]);
    setRoute(null);
    setIsStreaming(true);
    try {
      for await (const event of streamChat(sessionId, message, auth.token)) {
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
          setMessages((prev) => [...prev, { role: "assistant", content: event.data.answer }]);
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

  return (
    <main className="flex flex-col h-screen">
      <div className="flex items-center justify-between px-4 py-1 border-b text-sm text-slate-600">
        <span>{auth.email}</span>
        <button onClick={onLogout}>Log out</button>
      </div>
      {activeAlert && (
        <div className="bg-amber-100 dark:bg-amber-950 border-b border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200 px-4 py-2 flex items-center justify-between gap-4">
          <span className="text-sm">
            Hazard alert: conditions near your last query turned <strong>{activeAlert.verdict}</strong> —{" "}
            {activeAlert.reasons.join("; ")}
          </span>
          <button
            onClick={() => setActiveAlert(null)}
            className="text-amber-900 dark:text-amber-200 text-sm shrink-0"
            aria-label="Dismiss alert"
          >
            Dismiss
          </button>
        </div>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 flex-1 min-h-0">
        <div className="border-r h-1/3 md:h-full">
          <ChatPanel messages={messages} onSend={handleSend} isStreaming={isStreaming} />
        </div>
        <div className="border-r h-1/3 md:h-full">
          <ReasoningTrace trace={trace} />
        </div>
        <div className="h-1/3 md:h-full">
          <MapView lat={location?.lat ?? null} lon={location?.lon ?? null} route={route ?? undefined} />
        </div>
      </div>
    </main>
  );
}
