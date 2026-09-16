import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ReasoningTrace } from "./ReasoningTrace";
import { TraceEntry } from "@/lib/types";

describe("ReasoningTrace", () => {
  const sampleTrace: TraceEntry[] = [
    {
      agent: "planner",
      inputs: { message: "Can I fish near Mangaluru?" },
      output: { intent: "fishing safety", place_name: "Mangaluru" },
      sources: [],
      fetched_at: null,
      is_cached: false,
    },
    {
      agent: "geospatial",
      inputs: { place_name: "Mangaluru" },
      output: { lat: 12.91, lon: 74.85, resolved_name: "Mangaluru Coastal Sector" },
      sources: ["OSM/Nominatim"],
      fetched_at: null,
      is_cached: false,
    },
    {
      agent: "weather",
      inputs: { lat: 12.91, lon: 74.85 },
      output: {
        tide_height_m: 1.25,
        next_high_tide: { time: "2026-09-16T12:00:00Z", height_m: 1.8 },
      },
      sources: ["INCOIS", "IMD"],
      fetched_at: "2026-09-16T06:00:00Z",
      is_cached: true,
    },
  ];

  it("renders empty state when trace is empty", () => {
    const html = renderToStaticMarkup(<ReasoningTrace trace={[]} />);
    expect(html).toContain("No Active Reasoning Trace");
  });

  it("renders all pipeline steps with sequential numbering and agent badges", () => {
    const html = renderToStaticMarkup(<ReasoningTrace trace={sampleTrace} isStreaming={false} />);
    expect(html).toContain("Multi-Agent Reasoning Trace");
    expect(html).toContain("3 steps");
    expect(html).toContain("Planner");
    expect(html).toContain("Geospatial");
    expect(html).toContain("Weather");
    expect(html).toContain("01");
    expect(html).toContain("02");
    expect(html).toContain("03");
  });

  it("renders cache fallback snapshot indicator", () => {
    const html = renderToStaticMarkup(<ReasoningTrace trace={sampleTrace} />);
    expect(html).toContain("Snapshot Fallback:");
  });

  it("renders tide information in weather agent output", () => {
    const html = renderToStaticMarkup(<ReasoningTrace trace={sampleTrace} />);
    expect(html).toContain("Current Tide: 1.25m");
    expect(html).toContain("Next high:");
  });
});
