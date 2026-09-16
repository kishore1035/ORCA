// frontend/components/AgentWorkflowPanel.tsx
"use client";

import React, { useState } from "react";
import { X } from "lucide-react";
import { TraceEntry } from "@/lib/types";
import { WorkflowGraph } from "./WorkflowGraph";
import { ReasoningTrace } from "./ReasoningTrace";

interface AgentWorkflowPanelProps {
  trace: TraceEntry[];
  isStreaming?: boolean;
  onClose?: () => void;
}

export function AgentWorkflowPanel({
  trace,
  isStreaming = false,
  onClose,
}: AgentWorkflowPanelProps) {
  const [viewMode, setViewMode] = useState<"graph" | "trace">("graph");

  return (
    <div className="h-full flex flex-col min-h-0 bg-slate-50/50 border-r border-slate-200/90">
      {/* View Switcher Header (Light UI Theme matching ORCA workspace) */}
      <div className="px-3.5 py-2.5 bg-white/95 backdrop-blur-md border-b border-slate-200/90 flex items-center justify-between text-xs shrink-0 z-10 shadow-2xs">
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${
              isStreaming
                ? "bg-emerald-500 animate-ping shadow-[0_0_8px_#10b981]"
                : trace.length > 0
                ? "bg-emerald-500 shadow-[0_0_8px_#10b981]"
                : "bg-slate-400"
            }`}
          />
          <span className="font-bold text-slate-800 tracking-tight text-xs">
            Multi-Agent Workflow
          </span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 border border-slate-200/80 font-semibold">
            {isStreaming ? "ACTIVE DISPATCH" : trace.length > 0 ? `${trace.length} STEPS` : "IDLE"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* View Toggle Pill */}
          <div className="flex items-center p-0.5 rounded-lg bg-slate-100 border border-slate-200 text-[11px] font-medium">
            <button
              type="button"
              onClick={() => setViewMode("graph")}
              className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                viewMode === "graph"
                  ? "bg-white text-slate-900 font-semibold shadow-2xs border border-slate-200/80"
                  : "text-slate-500 hover:text-slate-900"
              }`}
            >
              Graph View
            </button>
            <button
              type="button"
              onClick={() => setViewMode("trace")}
              className={`px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                viewMode === "trace"
                  ? "bg-white text-slate-900 font-semibold shadow-2xs border border-slate-200/80"
                  : "text-slate-500 hover:text-slate-900"
              }`}
            >
              Step Trace
            </button>
          </div>

          {/* Collapse button to slide back to Chat + Map */}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer text-xs"
              title="Collapse Workflow Panel"
              aria-label="Collapse Workflow Panel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 min-h-0 relative overflow-hidden bg-slate-50/60">
        {viewMode === "graph" ? (
          <WorkflowGraph trace={trace} isStreaming={isStreaming} />
        ) : (
          <div className="h-full overflow-y-auto bg-slate-50/40">
            <ReasoningTrace trace={trace} isStreaming={isStreaming} />
          </div>
        )}
      </div>
    </div>
  );
}
