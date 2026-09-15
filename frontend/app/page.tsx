// frontend/app/page.tsx
"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { ChatPanel } from "@/components/ChatPanel";
import { ReasoningTrace } from "@/components/ReasoningTrace";
import { streamChat, fetchHistory } from "@/lib/chatClient";
import { ChatMessage, TraceEntry } from "@/lib/types";

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
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId] = useState(getOrCreateSessionId);

  useEffect(() => {
    fetchHistory(sessionId)
      .then(setMessages)
      .catch(() => {
        // No persisted history yet, or the backend is unreachable -- start fresh.
      });
  }, [sessionId]);

  async function handleSend(message: string) {
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setTrace([]);
    setIsStreaming(true);
    try {
      for await (const event of streamChat(sessionId, message)) {
        if (event.type === "trace") {
          setTrace((prev) => [...prev, event.data]);
          if (event.data.agent === "geospatial") {
            const { lat, lon } = event.data.output as { lat: number; lon: number };
            if (typeof lat === "number" && typeof lon === "number") setLocation({ lat, lon });
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
    <main className="grid grid-cols-1 md:grid-cols-3 h-screen">
      <div className="border-r h-1/3 md:h-full">
        <ChatPanel messages={messages} onSend={handleSend} isStreaming={isStreaming} />
      </div>
      <div className="border-r h-1/3 md:h-full">
        <ReasoningTrace trace={trace} />
      </div>
      <div className="h-1/3 md:h-full">
        <MapView lat={location?.lat ?? null} lon={location?.lon ?? null} />
      </div>
    </main>
  );
}
