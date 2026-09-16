// frontend/components/WhatIfCard.tsx
"use client";

import React from "react";
import { Clock, TrendingDown, TrendingUp } from "lucide-react";
import { WhatIfComparison } from "@/lib/types";

interface WhatIfCardProps {
  comparison: WhatIfComparison;
}

export function WhatIfCard({ comparison }: WhatIfCardProps) {
  const {
    original_time,
    original_risk_score,
    original_risk_level,
    alternative_time,
    alternative_risk_score,
    alternative_risk_level,
    differences,
    verdict,
  } = comparison;

  const scoreDelta = alternative_risk_score - original_risk_score;
  const isSafer = scoreDelta < 0;

  return (
    <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-950/30 p-4 shadow-sm mb-4">
      <div className="flex items-center justify-between gap-2 pb-2 border-b border-indigo-100 dark:border-indigo-900/50">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-indigo-700 dark:text-indigo-300" />
          <h4 className="text-sm font-bold text-indigo-950 dark:text-indigo-200">
            What-If Departure Comparison
          </h4>
        </div>
        <span
          className={`px-2.5 py-0.5 rounded text-xs font-semibold inline-flex items-center gap-1 ${
            isSafer
              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/60 dark:text-emerald-200"
              : "bg-orange-100 text-orange-800 dark:bg-orange-900/60 dark:text-orange-200"
          }`}
        >
          {isSafer ? (
            <>
              <TrendingDown className="w-3 h-3 text-emerald-700" /> {Math.abs(scoreDelta)} pts Risk Reduction
            </>
          ) : (
            <>
              <TrendingUp className="w-3 h-3 text-orange-700" /> {scoreDelta} pts Risk Increase
            </>
          )}
        </span>
      </div>

      {/* Comparison Badges */}
      <div className="grid grid-cols-2 gap-3 my-3">
        <div className="p-2.5 rounded-lg bg-white/80 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
          <div className="text-[11px] text-slate-500 font-medium">Original Departure:</div>
          <div className="text-base font-bold text-slate-800 dark:text-slate-100">
            {original_time}
          </div>
          <div className="text-xs font-semibold text-orange-600 dark:text-orange-400 mt-0.5">
            Risk: {original_risk_score} ({original_risk_level})
          </div>
        </div>

        <div className="p-2.5 rounded-lg bg-white/80 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800">
          <div className="text-[11px] text-slate-500 font-medium">Alternative Departure:</div>
          <div className="text-base font-bold text-slate-800 dark:text-slate-100">
            {alternative_time}
          </div>
          <div
            className={`text-xs font-semibold mt-0.5 ${
              isSafer
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-red-600 dark:text-red-400"
            }`}
          >
            Risk: {alternative_risk_score} ({alternative_risk_level})
          </div>
        </div>
      </div>

      {/* Parameter Differences Table */}
      {differences && differences.length > 0 && (
        <div className="overflow-x-auto my-2">
          <table className="w-full text-xs text-left border-collapse">
            <thead>
              <tr className="border-b border-indigo-100 dark:border-indigo-900 text-slate-500">
                <th className="py-1 px-2 font-medium">Parameter</th>
                <th className="py-1 px-2 font-medium">{original_time}</th>
                <th className="py-1 px-2 font-medium">{alternative_time}</th>
                <th className="py-1 px-2 font-medium">Change</th>
                <th className="py-1 px-2 font-medium">Impact</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-indigo-100/60 dark:divide-indigo-900/30">
              {differences.map((diff, i) => (
                <tr key={i} className="text-slate-700 dark:text-slate-300">
                  <td className="py-1.5 px-2 font-medium">{diff.parameter}</td>
                  <td className="py-1.5 px-2 font-mono">{diff.original}</td>
                  <td className="py-1.5 px-2 font-mono">{diff.alternative}</td>
                  <td className="py-1.5 px-2 font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                    {diff.delta}
                  </td>
                  <td className="py-1.5 px-2 text-[11px] text-slate-500">{diff.impact}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Narrative Verdict */}
      <div className="mt-2 text-xs text-indigo-950 dark:text-indigo-200 leading-relaxed font-medium">
        {verdict}
      </div>
    </div>
  );
}
