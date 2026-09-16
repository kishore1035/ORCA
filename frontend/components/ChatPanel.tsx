import { useEffect, useRef, useState } from "react";
import { Waves, MapPin, AlertTriangle, Check, Fish, Clock, Zap, Compass, ChevronDown, ChevronRight } from "lucide-react";
import { ChatMessage, TraceEntry } from "@/lib/types";
import { RecommendationHero } from "./RecommendationHero";
import { WhatIfCard } from "./WhatIfCard";
import { EvidencePanel } from "./EvidencePanel";
import { MarkdownContent } from "./MarkdownContent";
import { PromptInput } from "./ui/ai-chat-input";

interface ChatPanelProps {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  isStreaming: boolean;
  currentTrace?: TraceEntry[];
}

const DEMO_QUICK_PROMPTS = [
  {
    label: "Can I go fishing near Mangaluru tomorrow at 6 AM?",
    query: "Can I go fishing near Mangaluru tomorrow at 6 AM?",
    iconType: "fish" as const,
  },
  {
    label: "What if I leave at 11 AM instead?",
    query: "What if I leave at 11 AM instead?",
    iconType: "clock" as const,
  },
  {
    label: "Where is the nearest fishing zone near Kochi?",
    query: "Where is the nearest fishing zone near Kochi?",
    iconType: "compass" as const,
  },
  {
    label: "Any cyclone or lightning alerts near Mangaluru?",
    query: "Any cyclone or lightning alerts near Mangaluru?",
    iconType: "zap" as const,
  },
];

const SUGGESTED_LOCATIONS = [
  "Mangaluru Coast",
  "Kochi Fishing Harbour",
  "Veraval Port",
  "Visakhapatnam",
  "Chennai Coast",
];

type MessageKind = "clarification" | "error" | "answer";

function getMessageKind(msg: ChatMessage): MessageKind {
  if (msg.is_error || msg.message_type === "error") return "error";
  const text = msg.content.toLowerCase();
  if (
    text.includes("something went wrong") ||
    text.includes("unable to complete") ||
    text.includes("unable to process") ||
    text.includes("failed to") ||
    text.includes("error:")
  ) {
    return "error";
  }
  if (msg.message_type === "clarification") return "clarification";
  if (!msg.risk && (!msg.evidence || msg.evidence.length === 0)) {
    if (
      msg.content.includes("?") ||
      text.includes("need a location") ||
      text.includes("which coast") ||
      text.includes("which port") ||
      text.includes("coordinates") ||
      text.includes("specify")
    ) {
      return "clarification";
    }
  }
  return "answer";
}

function getAgentStreamingStatus(trace?: TraceEntry[]): string {
  if (!trace || trace.length === 0) {
    return "Initializing LangGraph multi-agent pipeline...";
  }
  const last = trace[trace.length - 1];
  switch (last.agent) {
    case "planner":
      return "Planner agent building orchestration DAG...";
    case "geospatial":
      return "Geospatial agent resolving sector coordinates & bathymetry...";
    case "weather":
      return "Weather agent fetching INCOIS ocean forecast & IMD warnings...";
    case "risk":
      return "Risk engine calculating wave, wind, and safety scores...";
    case "ocean_analytics":
      return "Ocean analytics agent auditing ISRO SST & chlorophyll data...";
    case "reporting":
      return "Reporting agent synthesizing grounded marine advisory...";
    default:
      return `Agent ${last.agent} executing step #${trace.length}...`;
  }
}

export function ChatPanel({
  messages,
  onSend,
  isStreaming,
  currentTrace,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [showEvidenceFor, setShowEvidenceFor] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll when messages update or during streaming
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming, currentTrace]);

  function handlePromptClick(query: string) {
    if (isStreaming) return;
    onSend(query);
  }

  return (
    <div className="flex flex-col h-full bg-slate-50/50">
      {/* ── DEMO SCENARIO QUICK PROMPT BAR (High Contrast & Spacing) ── */}
      <div className="px-4 py-3 bg-white border-b border-slate-200/90 shadow-2xs shrink-0">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-bold text-slate-600 uppercase tracking-wider">
            Verified Demo Scenarios
          </span>
          <span className="text-[10px] font-mono text-slate-400">
            One-tap prompts
          </span>
        </div>
        <div className="flex flex-wrap gap-2">
          {DEMO_QUICK_PROMPTS.map((p, idx) => (
            <button
              key={idx}
              onClick={() => handlePromptClick(p.query)}
              disabled={isStreaming}
              className="group text-xs px-3 py-1.5 rounded-xl bg-slate-100/90 hover:bg-black text-slate-800 hover:text-white border border-slate-300/80 hover:border-black font-medium transition-all shadow-2xs hover:shadow-xs disabled:opacity-50 text-left flex items-center gap-1.5"
            >
              <span className="opacity-80 group-hover:opacity-100">
                {p.iconType === "fish" && <Fish className="w-3.5 h-3.5" />}
                {p.iconType === "clock" && <Clock className="w-3.5 h-3.5" />}
                {p.iconType === "compass" && <Compass className="w-3.5 h-3.5" />}
                {p.iconType === "zap" && <Zap className="w-3.5 h-3.5" />}
              </span>
              <span>{p.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* ── CHAT MESSAGES LOG ── */}
      <div className="flex-1 overflow-y-auto space-y-5 p-4 sm:p-5">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center min-h-[340px] text-center p-6 sm:p-8 bg-white/80 rounded-3xl border border-slate-200/80 shadow-2xs my-auto">
            <div className="w-14 h-14 rounded-2xl bg-slate-900 text-white flex items-center justify-center mx-auto mb-3.5 shadow-md ring-4 ring-slate-100">
              <Waves className="w-6 h-6 text-sky-400" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 tracking-tight">
              ORCA Marine Reasoning Assistant
            </h3>
            <p className="text-xs text-slate-600 max-w-md mx-auto mt-1.5 leading-relaxed">
              Ask natural-language marine safety, fishing advisories, or coastal weather queries. Every assessment is grounded in official <strong>INCOIS</strong> ocean forecasts, <strong>IMD</strong> meteorological warnings, and <strong>ISRO</strong> satellite telemetry.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-2 mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-500 font-medium">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-slate-100 border border-slate-200">
                <Check className="w-3 h-3 text-emerald-600" /> Wave & Swell Heights
              </span>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-slate-100 border border-slate-200">
                <Check className="w-3 h-3 text-emerald-600" /> Potential Fishing Zones (PFZ)
              </span>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-slate-100 border border-slate-200">
                <Check className="w-3 h-3 text-emerald-600" /> Cyclone & Lightning Alerts
              </span>
            </div>
          </div>
        )}

        {messages.map((m, i) => {
          if (m.role === "user") {
            return (
              <div key={i} className="text-right flex justify-end">
                <div className="inline-block max-w-[85%] rounded-2xl rounded-tr-xs px-4 py-2.5 bg-black text-white text-sm font-medium shadow-xs leading-relaxed text-left">
                  {m.content}
                </div>
              </div>
            );
          }

          const kind = getMessageKind(m);

          return (
            <div key={i} className="text-left space-y-3 max-w-3xl">
              {/* 1. HERO RECOMMENDATION CARD (If risk assessment is available) */}
              {m.risk && (
                <RecommendationHero
                  risk={m.risk}
                  verification={m.verification}
                  sources={m.verification?.sources || ["INCOIS", "IMD", "ISRO/MOSDAC"]}
                  location={m.location}
                  evidence={m.evidence}
                />
              )}

              {/* 2. WHAT-IF DEPARTURE COMPARISON */}
              {m.what_if && <WhatIfCard comparison={m.what_if} />}

              {/* 3. VISUALLY DIFFERENTIATED MESSAGE CARDS */}
              {kind === "clarification" && (
                <div className="p-4 sm:p-5 rounded-2xl bg-slate-100/90 border border-slate-300 text-slate-900 shadow-2xs space-y-3">
                  <div className="flex items-center gap-2 text-xs font-bold text-slate-700">
                    <span className="w-5 h-5 rounded-md bg-white border border-slate-300 flex items-center justify-center text-xs shadow-2xs">
                      <MapPin className="w-3.5 h-3.5 text-slate-700" />
                    </span>
                    <span>Location / Query Clarification Needed</span>
                  </div>
                  <div className="text-sm font-medium leading-relaxed">
                    <MarkdownContent content={m.content} />
                  </div>
                  {/* Quick suggested coastal areas */}
                  <div className="pt-2 border-t border-slate-200/80 flex flex-wrap items-center gap-1.5">
                    <span className="text-[11px] text-slate-500 font-semibold mr-1">
                      Quick select:
                    </span>
                    {SUGGESTED_LOCATIONS.map((loc, lIdx) => (
                      <button
                        key={lIdx}
                        onClick={() => handlePromptClick(`Is it safe to go fishing near ${loc}?`)}
                        disabled={isStreaming}
                        className="text-[11px] px-2.5 py-1 rounded-lg bg-white hover:bg-black text-slate-700 hover:text-white border border-slate-300 font-medium transition-colors shadow-2xs"
                      >
                        {loc}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {kind === "error" && (
                <div className="p-4 sm:p-5 rounded-2xl bg-rose-50/80 border border-rose-200 text-rose-950 shadow-2xs space-y-2.5">
                  <div className="flex items-center gap-2 text-xs font-bold text-rose-800">
                    <span className="w-5 h-5 rounded-md bg-rose-100 border border-rose-200 flex items-center justify-center text-xs shadow-2xs">
                      <AlertTriangle className="w-3.5 h-3.5 text-rose-700" />
                    </span>
                    <span>Telemetry Processing Notice</span>
                  </div>
                  <div className="text-sm font-medium leading-relaxed text-rose-900">
                    {m.content}
                  </div>
                  <p className="text-xs text-rose-700 leading-normal">
                    ORCA could not complete the multi-agent pipeline for this request. Please verify that the coastal coordinates or harbour name are within Indian waters, or retry your query.
                  </p>
                </div>
              )}

              {kind === "answer" && (
                <div className="p-4 sm:p-5 rounded-2xl bg-white border border-sky-200/90 text-slate-900 shadow-[0_2px_12px_rgba(0,0,0,0.03)] ring-1 ring-sky-100/60 space-y-3">
                  <div className="flex items-center justify-between gap-2 pb-2 border-b border-slate-100 text-xs">
                    <div className="flex items-center gap-1.5 font-bold text-slate-800">
                      <Check className="w-3.5 h-3.5 text-sky-600" />
                      <span>Synthesized Marine Advisory</span>
                    </div>
                    <span className="text-[10px] font-mono text-slate-400">
                      INCOIS · IMD Grounded
                    </span>
                  </div>
                  <div className="text-sm text-slate-800 leading-relaxed font-normal">
                    <MarkdownContent content={m.content} />
                  </div>
                </div>
              )}

              {/* 4. GROUNDING EVIDENCE ACCORDION */}
              {m.evidence && m.evidence.length > 0 && (
                <div className="pt-1">
                  <button
                    onClick={() => setShowEvidenceFor(showEvidenceFor === i ? null : i)}
                    className="text-xs text-slate-800 font-semibold hover:text-black underline underline-offset-3 flex items-center gap-1.5 transition-colors"
                  >
                    {showEvidenceFor === i ? (
                      <ChevronDown className="w-3.5 h-3.5 text-slate-600" />
                    ) : (
                      <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
                    )}
                    <span>
                      {showEvidenceFor === i ? "Hide" : "Show"} Grounding Evidence & Observations ({m.evidence.length} metrics)
                    </span>
                  </button>
                  {showEvidenceFor === i && (
                    <div className="mt-2.5">
                      <EvidencePanel evidence={m.evidence} verification={m.verification} />
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {/* ── LOADING & PIPELINE TYPING INDICATOR ── */}
        {isStreaming && (
          <div className="space-y-3 max-w-3xl">
            <RecommendationHero isLoading={true} />
            <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex items-center gap-3">
              <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-slate-100 border border-slate-200 shrink-0">
                <span className="w-2 h-2 rounded-full bg-slate-700 animate-wave-dot-1" />
                <span className="w-2 h-2 rounded-full bg-slate-700 animate-wave-dot-2" />
                <span className="w-2 h-2 rounded-full bg-slate-700 animate-wave-dot-3" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold text-slate-900 truncate">
                  {getAgentStreamingStatus(currentTrace)}
                </div>
                <div className="text-[10px] text-slate-400 font-mono">
                  LangGraph Orchestration · Live Evidence Synthesis
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── ANIMATED SPRING PROMPT INPUT (Cubic-Bezier Physics & Fluid Morphing) ── */}
      <div className="p-3 sm:p-4 bg-transparent shrink-0 flex items-center justify-center">
        <PromptInput
          value={input}
          onChange={setInput}
          onSubmit={(val) => {
            if (!val.trim() || isStreaming) return;
            onSend(val.trim());
            setInput("");
          }}
          placeholder="Ask e.g. 'Can I fish near Mangaluru tomorrow at 6 AM?'"
          className="max-w-full mx-auto"
        />
      </div>
    </div>
  );
}
