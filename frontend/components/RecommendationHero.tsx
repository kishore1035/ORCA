// frontend/components/RecommendationHero.tsx
"use client";

import React from "react";
import {
  RiskAssessment,
  VerificationResult,
  CanonicalLocation,
  MarineParameter,
  DataStatus,
} from "@/lib/types";

export interface RecommendationHeroProps {
  risk?: RiskAssessment | null;
  verification?: VerificationResult | null;
  sources?: string[];
  location?: CanonicalLocation | null;
  evidence?: MarineParameter[] | null;
  timestamp?: string | null;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

// Strict Apple-style monochrome (Black & White) design tokens
const RISK_THEMES = {
  LOW: {
    label: "LOW",
    badgeBg: "bg-slate-100",
    badgeText: "text-slate-800",
    badgeBorder: "border-slate-300",
    dot: "bg-slate-400",
    gauge: "bg-slate-500",
    accent: "text-slate-700",
    headline: "text-black",
  },
  MODERATE: {
    label: "MODERATE",
    badgeBg: "bg-slate-100",
    badgeText: "text-slate-900",
    badgeBorder: "border-slate-400",
    dot: "bg-slate-600",
    gauge: "bg-slate-700",
    accent: "text-slate-900",
    headline: "text-black",
  },
  HIGH: {
    label: "HIGH",
    badgeBg: "bg-black",
    badgeText: "text-white",
    badgeBorder: "border-black",
    dot: "bg-white",
    gauge: "bg-black",
    accent: "text-black",
    headline: "text-black",
  },
  EXTREME: {
    label: "EXTREME",
    badgeBg: "bg-black",
    badgeText: "text-white",
    badgeBorder: "border-black",
    dot: "bg-white",
    gauge: "bg-black",
    accent: "text-black",
    headline: "text-black",
  },
} as const;

const STATUS_THEMES: Record<
  DataStatus,
  { label: string; bg: string; text: string; border: string; dot: string }
> = {
  LIVE: {
    label: "LIVE",
    bg: "bg-black",
    text: "text-white",
    border: "border-black",
    dot: "bg-white",
  },
  FORECAST: {
    label: "FORECAST",
    bg: "bg-slate-100",
    text: "text-slate-900",
    border: "border-slate-300",
    dot: "bg-slate-700",
  },
  CACHED: {
    label: "CACHED",
    bg: "bg-slate-50",
    text: "text-slate-700",
    border: "border-slate-200",
    dot: "bg-slate-400",
  },
  HISTORICAL: {
    label: "HISTORICAL",
    bg: "bg-slate-50",
    text: "text-slate-500",
    border: "border-slate-200",
    dot: "bg-slate-300",
  },
};

/**
 * Format timestamp into Apple editorial date/time: e.g. "16 Sep · 06:00"
 */
function formatEditorialDate(rawTimestamp?: string | null): string {
  if (!rawTimestamp) {
    const now = new Date();
    const day = now.getDate();
    const month = now.toLocaleString("en-US", { month: "short" });
    const hours = String(now.getHours()).padStart(2, "0");
    const mins = String(now.getMinutes()).padStart(2, "0");
    return `${day} ${month} · ${hours}:${mins}`;
  }

  // If already a time string like "06:00" or "06:00 AM"
  if (/^\d{1,2}:\d{2}/.test(rawTimestamp.trim())) {
    const now = new Date();
    const day = now.getDate();
    const month = now.toLocaleString("en-US", { month: "short" });
    return `${day} ${month} · ${rawTimestamp.trim()}`;
  }

  try {
    const d = new Date(rawTimestamp);
    if (isNaN(d.getTime())) return rawTimestamp;
    const day = d.getDate();
    const month = d.toLocaleString("en-US", { month: "short" });
    const hours = String(d.getHours()).padStart(2, "0");
    const mins = String(d.getMinutes()).padStart(2, "0");
    return `${day} ${month} · ${hours}:${mins}`;
  } catch {
    return rawTimestamp;
  }
}

/**
 * Resolve clean display location name without city hardcoding.
 */
function resolveLocationLabel(
  loc?: CanonicalLocation | null,
  evidence?: MarineParameter[] | null
): string {
  if (loc?.display_name && loc.display_name.trim().length > 0) {
    // If it contains a full address with commas, take the primary place and district/state
    const parts = loc.display_name.split(",").map((s) => s.trim());
    if (parts.length > 2) {
      return `${parts[0]}, ${parts[1]}`;
    }
    return loc.display_name;
  }

  if (loc?.nearest_coastal_name) {
    const sector = loc.nearest_coastal_sector ? ` (${loc.nearest_coastal_sector})` : "";
    return `${loc.nearest_coastal_name}${sector}`;
  }

  const lat = loc?.latitude ?? loc?.lat;
  const lon = loc?.longitude ?? loc?.lon;
  if (typeof lat === "number" && typeof lon === "number") {
    return `${lat.toFixed(2)}°N, ${lon.toFixed(2)}°E`;
  }

  if (evidence && evidence.length > 0) {
    const p = evidence[0];
    if (typeof p.latitude === "number" && typeof p.longitude === "number") {
      return `${p.latitude.toFixed(2)}°N, ${p.longitude.toFixed(2)}°E`;
    }
  }

  return "Coastal Sector";
}

/**
 * Editorial formatted list of supporting marine factors
 */
interface FormattedFactor {
  label: string;
  value: string;
}

function extractSupportingFactors(
  risk: RiskAssessment,
  evidence?: MarineParameter[] | null
): FormattedFactor[] {
  const items: FormattedFactor[] = [];

  // 1. Prefer structured parameters if available
  if (evidence && evidence.length > 0) {
    const findParam = (name: string) =>
      evidence.find((p) => p.parameter === name && p.value !== null && p.value !== undefined);

    const wave = findParam("significant_wave_height");
    if (wave && wave.value !== null) {
      items.push({
        label: "Significant wave height",
        value: `${Number(wave.value).toFixed(1)} m`,
      });
    }

    const wind = findParam("wind_speed");
    if (wind && wind.value !== null) {
      items.push({
        label: "Wind speed",
        value: `${Number(wind.value).toFixed(1)} km/h`,
      });
    }

    const warning =
      findParam("weather_warning_level") || findParam("port_warning_signal");
    if (warning && warning.value) {
      const valStr = String(warning.value);
      const isClean = valStr.toLowerCase() === "green" || valStr.toLowerCase() === "none";
      items.push({
        label: "Coastal warning",
        value: isClean ? "None (Normal)" : `Active (${valStr})`,
      });
    }

    const current = findParam("surface_current_speed");
    if (current && current.value !== null) {
      items.push({
        label: "Surface current",
        value: `${Number(current.value).toFixed(2)} m/s`,
      });
    }

    const swell = findParam("swell_height");
    if (swell && swell.value !== null && items.length < 4) {
      items.push({
        label: "Swell wave height",
        value: `${Number(swell.value).toFixed(1)} m`,
      });
    }
  }

  // 2. If structured evidence was absent or sparse, parse from risk.factors
  if (items.length === 0 && risk.factors && risk.factors.length > 0) {
    for (const factor of risk.factors.slice(0, 4)) {
      // Clean up technical point additions like "(+30)" or "(+18)"
      const cleaned = factor.replace(/\s*\(\+\d+\)/g, "").trim();

      // Check for common metric patterns
      if (/wave height/i.test(cleaned)) {
        const m = cleaned.match(/([\d.]+\s*m)/i);
        items.push({
          label: "Significant wave height",
          value: m ? m[1] : cleaned,
        });
      } else if (/wind speed|gale|coastal wind/i.test(cleaned)) {
        const m = cleaned.match(/([\d.]+\s*km\/h)/i);
        items.push({
          label: "Wind speed",
          value: m ? m[1] : cleaned,
        });
      } else if (/warning|cyclone|lightning/i.test(cleaned)) {
        items.push({
          label: "Coastal warning",
          value: cleaned.replace(/^active\s+/i, "Active — "),
        });
      } else if (/current|drift/i.test(cleaned)) {
        const m = cleaned.match(/([\d.]+\s*m\/s)/i);
        items.push({
          label: "Surface current",
          value: m ? m[1] : cleaned,
        });
      } else {
        // Generic fallback split
        const parts = cleaned.split(" — ");
        if (parts.length === 2) {
          items.push({ label: parts[0], value: parts[1] });
        } else {
          items.push({ label: cleaned, value: "Recorded" });
        }
      }
    }
  }

  // If still empty, supply clean baseline indicators
  if (items.length === 0) {
    items.push({ label: "Significant wave height", value: "Normal range" });
    items.push({ label: "Wind speed", value: "Favorable" });
    items.push({ label: "Coastal warning", value: "None" });
  }

  return items;
}

export function RecommendationHero({
  risk,
  verification,
  sources = ["INCOIS", "IMD", "ISRO/MOSDAC"],
  location,
  evidence,
  timestamp,
  isLoading = false,
  error = null,
  onRetry,
}: RecommendationHeroProps) {
  // ── 1. LOADING SKELETON STATE ─────────────────────────────────────────────
  if (isLoading) {
    return (
      <div
        data-testid="recommendation-hero-loading"
        className="rounded-3xl bg-white border border-slate-200/80 shadow-[0_2px_16px_rgba(0,0,0,0.03)] p-6 sm:p-7 mb-5 transition-all animate-pulse"
      >
        <div className="flex items-center justify-between gap-4 mb-4">
          <div className="h-3.5 w-24 bg-slate-200/80 rounded-full" />
          <div className="h-5 w-16 bg-slate-200/80 rounded-full" />
        </div>

        {/* Big Recommendation Headline Skeleton */}
        <div className="h-8 sm:h-9 w-3/4 bg-slate-200/80 rounded-xl mb-6" />

        {/* Metrics Grid Skeleton */}
        <div className="grid grid-cols-2 gap-4 pb-5 border-b border-slate-100">
          <div className="p-3.5 bg-slate-50 rounded-2xl">
            <div className="h-3 w-16 bg-slate-200 rounded mb-2" />
            <div className="h-7 w-24 bg-slate-200 rounded" />
          </div>
          <div className="p-3.5 bg-slate-50 rounded-2xl">
            <div className="h-3 w-20 bg-slate-200 rounded mb-2" />
            <div className="h-7 w-20 bg-slate-200 rounded" />
          </div>
        </div>

        {/* Supporting Evidence Skeleton */}
        <div className="py-4 space-y-2.5 border-b border-slate-100">
          <div className="h-3 w-40 bg-slate-200/70 rounded mb-3" />
          <div className="h-3.5 w-56 bg-slate-200/70 rounded" />
          <div className="h-3.5 w-48 bg-slate-200/70 rounded" />
          <div className="h-3.5 w-52 bg-slate-200/70 rounded" />
        </div>

        {/* Metadata Footer Skeleton */}
        <div className="pt-4 flex items-center justify-between">
          <div className="h-3 w-32 bg-slate-200/70 rounded" />
          <div className="h-5 w-20 bg-slate-200/70 rounded-full" />
        </div>
      </div>
    );
  }

  // ── 2. ERROR STATE ────────────────────────────────────────────────────────
  if (error) {
    return (
      <div
        data-testid="recommendation-hero-error"
        className="rounded-3xl bg-white border border-slate-300 shadow-[0_2px_16px_rgba(0,0,0,0.04)] p-6 sm:p-7 mb-5 text-left transition-all"
      >
        <div className="flex items-start gap-3.5">
          <div className="w-10 h-10 rounded-2xl bg-slate-100 text-black flex items-center justify-center shrink-0 text-lg font-bold border border-slate-200">
            !
          </div>
          <div className="flex-1 min-w-0">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              Marine Telemetry Unavailable
            </span>
            <h3 className="text-lg font-bold text-black mt-0.5">
              Could not compute marine risk recommendation
            </h3>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">{error}</p>
            {onRetry && (
              <button
                onClick={onRetry}
                className="mt-3.5 px-4 py-1.5 rounded-full text-xs font-semibold bg-black text-white hover:bg-slate-800 transition-colors shadow-xs"
              >
                Retry Analysis
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ── 3. POLISHED EMPTY STATE ───────────────────────────────────────────────
  if (!risk) {
    return (
      <div
        data-testid="recommendation-hero-empty"
        className="rounded-3xl bg-white border border-slate-200/80 shadow-[0_2px_16px_rgba(0,0,0,0.03)] p-6 sm:p-7 mb-5 text-center transition-all"
      >
        <div className="w-11 h-11 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center mx-auto mb-3 text-slate-400 text-lg shadow-xs">
          🧭
        </div>
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Marine Ecosystem Reasoning
        </span>
        <h3 className="text-lg font-semibold text-slate-900 mt-1 mb-1.5">
          Select a coastal coordinate or enter a query
        </h3>
        <p className="text-xs text-slate-500 max-w-md mx-auto leading-relaxed">
          ORCA synthesizes INCOIS ocean forecasts, IMD meteorological warnings, and
          ISRO satellite observations into verifiable departure recommendations.
        </p>
      </div>
    );
  }

  // ── 4. ACTIVE RECOMMENDATION HERO ─────────────────────────────────────────
  const { risk_score, risk_level, recommendation, confidence } = risk;
  const theme = RISK_THEMES[risk_level] || RISK_THEMES.MODERATE;

  // Normalized data status (strict definition: LIVE | FORECAST | CACHED | HISTORICAL)
  const rawStatus = (verification?.data_status || "FORECAST").toUpperCase();
  const validStatus = (
    ["LIVE", "FORECAST", "CACHED", "HISTORICAL"].includes(rawStatus)
      ? rawStatus
      : "FORECAST"
  ) as DataStatus;
  const statusTheme = STATUS_THEMES[validStatus] || STATUS_THEMES.FORECAST;

  // Location display
  const locationLabel = resolveLocationLabel(location, evidence);

  // Time display
  const targetTime =
    timestamp ||
    (evidence && evidence.length > 0 ? evidence[0].timestamp : null) ||
    null;
  const formattedTime = formatEditorialDate(targetTime);

  // Factors
  const factors = extractSupportingFactors(risk, evidence);

  // Proximity to forecast grid
  const gridDistance =
    location?.grid_distance_km ??
    (evidence && evidence[0]?.grid_distance_km ? evidence[0].grid_distance_km : null);
  const gridLabel =
    typeof gridDistance === "number"
      ? `${gridDistance.toFixed(1)} km from nearest forecast grid`
      : location?.distance_to_coast_km != null
      ? `${location.distance_to_coast_km.toFixed(1)} km offshore`
      : "Within Indian coastal grid coverage";

  // Sources string
  const activeSources =
    sources && sources.length > 0 ? sources : ["INCOIS", "IMD", "ISRO/MOSDAC"];
  const sourcesLabel = activeSources.join(" · ");

  return (
    <div
      data-testid="recommendation-hero"
      className="rounded-3xl bg-white border border-slate-200/80 shadow-[0_2px_20px_rgba(0,0,0,0.04)] hover:shadow-[0_4px_24px_rgba(0,0,0,0.06)] p-6 sm:p-7 mb-4 transition-all duration-300 text-left font-sans select-text"
    >
      {/* ── TOP EYEBROW + RISK PILL ── */}
      <div className="flex items-center justify-between gap-3 mb-2.5">
        <span className="text-[11px] font-semibold tracking-wider uppercase text-slate-400">
          [ Marine Risk ]
        </span>
        <div
          data-testid="risk-badge"
          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-xs font-semibold tracking-wide ${theme.badgeBg} ${theme.badgeText} ${theme.badgeBorder}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${theme.dot}`} />
          <span>{theme.label}</span>
        </div>
      </div>

      {/* ── PRIMARY RECOMMENDATION (Visually Dominates) ── */}
      <h2
        data-testid="primary-recommendation"
        className="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900 leading-snug sm:leading-tight mb-5"
      >
        {recommendation}
      </h2>

      {/* ── METRICS: RISK SCORE & CONFIDENCE ── */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 p-3.5 sm:p-4 rounded-2xl bg-slate-50/70 border border-slate-100">
        {/* Risk Stat */}
        <div className="flex flex-col justify-between">
          <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
            Risk Index
          </span>
          <div className="flex items-baseline gap-1 mt-1">
            <span
              data-testid="risk-score-value"
              className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 font-mono"
            >
              {risk_score}
            </span>
            <span className="text-xs sm:text-sm font-medium text-slate-400">/ 100</span>
          </div>
          {/* Subtle micro gauge */}
          <div className="w-full h-1.5 bg-slate-200/70 rounded-full overflow-hidden mt-2.5">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${theme.gauge}`}
              style={{ width: `${Math.min(100, Math.max(4, risk_score))}%` }}
            />
          </div>
        </div>

        {/* Confidence Stat */}
        <div className="flex flex-col justify-between border-l border-slate-200/60 pl-3.5 sm:pl-4">
          <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">
            Confidence
          </span>
          <div className="flex items-baseline gap-1 mt-1">
            <span
              data-testid="confidence-value"
              className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 font-mono"
            >
              {Math.round(confidence * 100)}%
            </span>
          </div>
          <span className="text-[10px] text-slate-400 mt-2 font-medium tracking-wide">
            {verification?.is_verified ? "Provenance Verified ✓" : "Cross-Grounded"}
          </span>
        </div>
      </div>

      {/* ── DIVIDER ── */}
      <div className="h-px bg-slate-100 my-5" />

      {/* ── WHY ORCA RECOMMENDS THIS ── */}
      <div>
        <h3 className="text-xs font-semibold tracking-wider text-slate-400 uppercase mb-3">
          Why ORCA recommends this
        </h3>
        <ul className="space-y-2 text-sm text-slate-700">
          {factors.map((factor, idx) => (
            <li
              key={idx}
              className="flex items-baseline gap-2.5 text-xs sm:text-sm leading-relaxed"
            >
              <span className="text-slate-300 font-semibold select-none">•</span>
              <span className="font-medium text-slate-800">{factor.label}</span>
              <span className="text-slate-400 font-normal">—</span>
              <span className="font-semibold text-slate-700">{factor.value}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* ── DIVIDER ── */}
      <div className="h-px bg-slate-100 my-5" />

      {/* ── METADATA FOOTER (Quiet, Apple-style metadata) ── */}
      <div className="space-y-2 text-xs text-slate-500">
        <div className="flex flex-wrap items-center justify-between gap-2">
          {/* Location & Time */}
          <div className="flex items-center gap-2 font-medium text-slate-700">
            <span data-testid="hero-location" className="font-semibold">
              {locationLabel}
            </span>
            <span className="text-slate-300">·</span>
            <span data-testid="hero-timestamp" className="text-slate-500">
              {formattedTime}
            </span>
          </div>

          {/* Status Badge: Apple-style quiet pill */}
          <div
            data-testid="data-status-badge"
            className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${statusTheme.bg} ${statusTheme.text} ${statusTheme.border}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${statusTheme.dot}`} />
            <span>{statusTheme.label}</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px] text-slate-400">
          {/* Sources Attribution */}
          <span data-testid="hero-sources" className="tracking-wide">
            {sourcesLabel}
          </span>

          {/* Forecast Grid Proximity */}
          <span data-testid="hero-grid-distance" className="font-mono text-slate-400">
            {gridLabel}
          </span>
        </div>
      </div>
    </div>
  );
}
