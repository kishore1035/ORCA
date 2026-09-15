// frontend/components/ChatPanel.tsx
"use client";
import { useEffect, useRef, useState, FormEvent } from "react";
import { ChatMessage } from "@/lib/types";
import { isSpeechRecognitionSupported, isSpeechSynthesisSupported, speak, startListening } from "@/lib/voice";

interface ChatPanelProps {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  isStreaming: boolean;
}

export function ChatPanel({ messages, onSend, isStreaming }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [speakAnswers, setSpeakAnswers] = useState(false);
  const lastSpokenCount = useRef(0);

  useEffect(() => {
    if (!speakAnswers) {
      lastSpokenCount.current = messages.length;
      return;
    }
    const last = messages[messages.length - 1];
    if (messages.length > lastSpokenCount.current && last?.role === "assistant") {
      speak(last.content);
    }
    lastSpokenCount.current = messages.length;
  }, [messages, speakAnswers]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    onSend(input.trim());
    setInput("");
  }

  function handleMicClick() {
    if (isListening) return;
    setIsListening(true);
    startListening(
      (text) => {
        setInput(text);
        setIsListening(false);
      },
      () => setIsListening(false)
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-2 p-4">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <span className="inline-block rounded-lg px-3 py-2 bg-slate-100">{m.content}</span>
          </div>
        ))}
        {isStreaming && <div className="text-left text-sm text-slate-400">thinking...</div>}
      </div>
      {isSpeechSynthesisSupported() && (
        <label className="flex items-center gap-2 px-4 text-sm text-slate-500">
          <input
            type="checkbox"
            checked={speakAnswers}
            onChange={(e) => setSpeakAnswers(e.target.checked)}
          />
          Read answers aloud
        </label>
      )}
      <form onSubmit={handleSubmit} className="flex gap-2 p-4 border-t">
        <input
          className="flex-1 border rounded px-3 py-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about weather, fishing zones, or safety..."
          disabled={isStreaming}
        />
        {isSpeechRecognitionSupported() && (
          <button
            type="button"
            onClick={handleMicClick}
            disabled={isStreaming || isListening}
            className="px-3 py-2 border rounded disabled:opacity-50"
            aria-label="Speak your question"
          >
            {isListening ? "Listening..." : "Mic"}
          </button>
        )}
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
          disabled={isStreaming}
        >
          Send
        </button>
      </form>
    </div>
  );
}
