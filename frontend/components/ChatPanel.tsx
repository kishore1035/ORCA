// frontend/components/ChatPanel.tsx
"use client";

import { useEffect, useRef, useState, FormEvent } from "react";
import { ChatMessage } from "@/lib/types";
import { RecommendationHero } from "@/components/RecommendationHero";
import { WhatIfCard } from "@/components/WhatIfCard";
import { EvidencePanel } from "@/components/EvidencePanel";
import {
  isSpeechRecognitionSupported,
  isSpeechSynthesisSupported,
  speak,
  startListening,
} from "@/lib/voice";

interface ChatPanelProps {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  isStreaming: boolean;
}

const DEMO_QUICK_PROMPTS = [
  {
    label: "🎣 Can I go fishing near Mangaluru tomorrow at 6 AM?",
    query: "Can I go fishing near Mangaluru tomorrow at 6 AM?",
  },
  {
    label: "⏰ What if I leave at 11 AM instead?",
    query: "What if I leave at 11 AM instead?",
  },
  {
    label: "🐟 Where is the nearest fishing zone near Kochi?",
    query: "Where is the nearest fishing zone near Kochi?",
  },
  {
    label: "⚡ Any cyclone or lightning alerts?",
    query: "Any cyclone or lightning alerts near Mangaluru?",
  },
];

export function ChatPanel({ messages, onSend, isStreaming }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [showEvidenceFor, setShowEvidenceFor] = useState<number | null>(null);
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

  function handlePromptClick(query: string) {
    if (isStreaming) return;
    onSend(query);
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
    <div className="flex flex-col h-full bg-slate-50/50">
      {/* Quick Prompt Bar */}
      <div className="p-3 border-b bg-white border-slate-200">
        <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
          Demo Scenarios
        </div>
        <div className="flex flex-wrap gap-1.5">
          {DEMO_QUICK_PROMPTS.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handlePromptClick(p.query)}
              disabled={isStreaming}
              className="text-xs px-2.5 py-1 rounded-full bg-slate-100 hover:bg-black text-slate-800 hover:text-white border border-slate-200 hover:border-black transition-colors disabled:opacity-50 text-left"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages List */}
      <div className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.length === 0 && (
          <div className="text-center py-12 px-4">
            <div className="w-12 h-12 rounded-full bg-slate-100 border border-slate-200 text-slate-900 flex items-center justify-center mx-auto mb-3 text-2xl font-bold shadow-xs">
              🌊
            </div>
            <h3 className="text-base font-bold text-slate-900">
              ORCA Marine Reasoning Assistant
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 leading-relaxed">
              Ask natural-language marine safety, fishing zone, or weather queries grounded in official
              INCOIS, IMD, and ISRO satellite observations.
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            {m.role === "user" ? (
              <span className="inline-block rounded-2xl px-4 py-2 bg-black text-white text-sm font-medium shadow-sm">
                {m.content}
              </span>
            ) : (
              <div className="space-y-3 max-w-3xl">
                {/* 1. HERO RECOMMENDATION CARD */}
                {m.risk && (
                  <RecommendationHero
                    risk={m.risk}
                    verification={m.verification}
                    sources={m.verification?.sources || ["INCOIS", "IMD", "ISRO/MOSDAC"]}
                    location={m.location}
                    evidence={m.evidence}
                  />
                )}

                {/* 2. WHAT-IF COMPARISON CARD */}
                {m.what_if && <WhatIfCard comparison={m.what_if} />}

                {/* 3. ASSISTANT SYNTHESIZED TEXT */}
                <div className="p-4 rounded-2xl bg-white border border-slate-200 text-sm text-slate-900 shadow-xs leading-relaxed whitespace-pre-wrap">
                  {m.content}
                </div>

                {/* 4. COLLAPSIBLE EVIDENCE ACCORDION */}
                {m.evidence && m.evidence.length > 0 && (
                  <div>
                    <button
                      onClick={() => setShowEvidenceFor(showEvidenceFor === i ? null : i)}
                      className="text-xs text-slate-900 font-semibold hover:text-black underline underline-offset-2 flex items-center gap-1"
                    >
                      <span>{showEvidenceFor === i ? "▼ Hide" : "▶ Show"} Grounding Evidence & Observations ({m.evidence.length} metrics)</span>
                    </button>
                    {showEvidenceFor === i && (
                      <div className="mt-2">
                        <EvidencePanel evidence={m.evidence} verification={m.verification} />
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
        {isStreaming && (
          <div className="space-y-3">
            <RecommendationHero isLoading={true} />
            <div className="flex items-center gap-2 text-xs text-slate-500 p-2">
              <span className="inline-block w-2 h-2 rounded-full bg-black animate-pulse" />
              <span>ORCA reasoning across INCOIS, IMD, and satellite evidence...</span>
            </div>
          </div>
        )}
      </div>

      {/* Voice Toggle Option */}
      {isSpeechSynthesisSupported() && (
        <div className="px-4 py-1.5 border-t border-slate-100 bg-white flex items-center justify-end">
          <label className="flex items-center gap-2 text-xs text-slate-500 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={speakAnswers}
              onChange={(e) => setSpeakAnswers(e.target.checked)}
              className="accent-black rounded"
            />
            <span>Read answers aloud</span>
          </label>
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="flex gap-2 p-3 border-t bg-white border-slate-200">
        <input
          className="flex-1 border border-slate-300 rounded-xl px-4 py-2.5 text-sm bg-slate-50 text-slate-900 focus:outline-none focus:ring-2 focus:ring-black"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask e.g. 'Can I fish near Mangaluru tomorrow at 6 AM?'"
          disabled={isStreaming}
        />
        {isSpeechRecognitionSupported() && (
          <button
            type="button"
            onClick={handleMicClick}
            disabled={isStreaming || isListening}
            className="px-3.5 py-2.5 border border-slate-300 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 disabled:opacity-50 text-xs font-semibold transition-colors"
            aria-label="Speak your question"
          >
            {isListening ? "Listening..." : "🎤 Speak"}
          </button>
        )}
        <button
          type="submit"
          className="px-5 py-2.5 bg-black hover:bg-slate-800 text-white text-sm font-semibold rounded-xl disabled:opacity-50 transition-colors shadow-xs"
          disabled={isStreaming || !input.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}
