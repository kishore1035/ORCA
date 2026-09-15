// frontend/app/page.tsx
"use client";
import { useState } from "react";
import dynamic from "next/dynamic";
import { ChatPanel } from "@/components/ChatPanel";
import { ReasoningTrace } from "@/components/ReasoningTrace";
import { streamChat } from "@/lib/chatClient";
import { ChatMessage, TraceEntry } from "@/lib/types";

const MapView = dynamic(() => import("@/components/MapView").then((m) => m.MapView), { ssr: false });

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());

  async function handleSend(message: string) {
    const priorMessages = messages;
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setTrace([]);
    setIsStreaming(true);
    try {
      for await (const event of streamChat(sessionId, message, priorMessages)) {
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
