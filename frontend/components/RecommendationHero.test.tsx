import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { RecommendationHero } from "./RecommendationHero";
import { RiskAssessment, VerificationResult, CanonicalLocation, MarineParameter } from "@/lib/types";

describe("RecommendationHero", () => {
  const baseRisk: RiskAssessment = {
    risk_score: 78,
    risk_level: "HIGH",
    factors: [
      "Significant wave height 2.3m exceeds cautionary limit (+30)",
      "Strong coastal wind 28.5 km/h (+22)",
      "Active IMD Orange Warning (+20)",
      "Surface current velocity 0.45 m/s (+5)",
    ],
    recommendation: "Avoid departure at 06:00",
    confidence: 0.89,
  };

  it("renders active recommendation hero with high visual hierarchy", () => {
    const html = renderToStaticMarkup(
      <RecommendationHero
        risk={baseRisk}
        verification={{
          is_verified: true,
          sources: ["INCOIS", "IMD", "ISRO/MOSDAC"],
          data_status: "FORECAST",
          checks_passed: [],
          issues: [],
          confidence: 0.9,
        }}
        sources={["INCOIS", "IMD", "ISRO/MOSDAC"]}
        location={{
          display_name: "Mangaluru, Karnataka",
          grid_distance_km: 2.3,
        }}
        timestamp="16 Sep · 06:00"
      />
    );

    // Primary recommendation visually dominates
    expect(html).toContain("Avoid departure at 06:00");
    // Marine Risk pill & level
    expect(html).toContain("[ Marine Risk ]");
    expect(html).toContain("HIGH");
    // Risk Score and Confidence
    expect(html).toContain("78");
    expect(html).toContain("/ 100");
    expect(html).toContain("89%");
    // Factors
    expect(html).toContain("Why ORCA recommends this");
    expect(html).toContain("Significant wave height");
    expect(html).toContain("Wind speed");
    // Location, date, sources, status pill, grid distance
    expect(html).toContain("Mangaluru, Karnataka");
    expect(html).toContain("16 Sep · 06:00");
    expect(html).toContain("INCOIS · IMD · ISRO/MOSDAC");
    expect(html).toContain("FORECAST");
    expect(html).toContain("2.3 km from nearest forecast grid");
  });

  it("renders all 4 data states correctly as Apple-style metadata pills", () => {
    const states = ["LIVE", "FORECAST", "CACHED", "HISTORICAL"] as const;

    for (const status of states) {
      const verification: VerificationResult = {
        is_verified: true,
        sources: ["INCOIS"],
        data_status: status,
        checks_passed: [],
        issues: [],
        confidence: 0.95,
      };

      const html = renderToStaticMarkup(
        <RecommendationHero risk={baseRisk} verification={verification} />
      );

      expect(html).toContain(status);
    }
  });

  it("renders correctly for various coastal locations without hardcoding", () => {
    const testLocations: Array<{ loc: CanonicalLocation; expectedText: string }> = [
      {
        loc: { display_name: "Veraval Fishing Harbour, Gujarat", grid_distance_km: 1.8 },
        expectedText: "Veraval Fishing Harbour, Gujarat",
      },
      {
        loc: { display_name: "Kavaratti Island, Lakshadweep", grid_distance_km: 3.1 },
        expectedText: "Kavaratti Island, Lakshadweep",
      },
      {
        loc: { display_name: "Diglipur Coastal Hamlet, Andaman & Nicobar", grid_distance_km: 4.5 },
        expectedText: "Diglipur Coastal Hamlet, Andaman &amp; Nicobar",
      },
      {
        loc: {
          latitude: 15.2,
          longitude: 73.1,
          is_offshore: true,
          distance_to_coast_km: 45.2,
        },
        expectedText: "15.20°N, 73.10°E",
      },
    ];

    for (const { loc, expectedText } of testLocations) {
      const html = renderToStaticMarkup(
        <RecommendationHero risk={baseRisk} location={loc} />
      );
      expect(html).toContain(expectedText);
    }
  });

  it("renders structured evidence parameters cleanly in editorial style", () => {
    const evidence: MarineParameter[] = [
      {
        parameter: "significant_wave_height",
        value: 2.3,
        unit: "m",
        latitude: 12.91,
        longitude: 74.85,
        timestamp: "2026-09-16T06:00:00Z",
        source: "INCOIS",
        data_status: "FORECAST",
        confidence: 0.92,
      },
      {
        parameter: "wind_speed",
        value: 28.5,
        unit: "km/h",
        latitude: 12.91,
        longitude: 74.85,
        timestamp: "2026-09-16T06:00:00Z",
        source: "INCOIS",
        data_status: "FORECAST",
        confidence: 0.9,
      },
      {
        parameter: "weather_warning_level",
        value: "Orange",
        unit: "advisory",
        latitude: 12.91,
        longitude: 74.85,
        timestamp: "2026-09-16T06:00:00Z",
        source: "IMD",
        data_status: "LIVE",
        confidence: 0.95,
      },
      {
        parameter: "surface_current_speed",
        value: 0.45,
        unit: "m/s",
        latitude: 12.91,
        longitude: 74.85,
        timestamp: "2026-09-16T06:00:00Z",
        source: "INCOIS",
        data_status: "FORECAST",
        confidence: 0.88,
      },
    ];

    const html = renderToStaticMarkup(
      <RecommendationHero risk={baseRisk} evidence={evidence} />
    );

    expect(html).toContain("Significant wave height");
    expect(html).toContain("2.3 m");
    expect(html).toContain("Wind speed");
    expect(html).toContain("28.5 km/h");
    expect(html).toContain("Coastal warning");
    expect(html).toContain("Active (Orange)");
    expect(html).toContain("Surface current");
    expect(html).toContain("0.45 m/s");
  });

  it("renders all risk levels (LOW, MODERATE, HIGH, EXTREME) with restrained semantic color", () => {
    const levels: Array<RiskAssessment["risk_level"]> = ["LOW", "MODERATE", "HIGH", "EXTREME"];
    for (const lvl of levels) {
      const risk: RiskAssessment = {
        ...baseRisk,
        risk_level: lvl,
        risk_score: lvl === "LOW" ? 15 : lvl === "MODERATE" ? 45 : lvl === "HIGH" ? 75 : 92,
      };
      const html = renderToStaticMarkup(<RecommendationHero risk={risk} />);
      expect(html).toContain(lvl);
      // Card remains clean light surface (bg-white), not flooded
      expect(html).toContain("bg-white");
    }
  });

  it("renders an Apple-style loading skeleton when isLoading=true", () => {
    const html = renderToStaticMarkup(<RecommendationHero isLoading={true} />);
    expect(html).toContain('data-testid="recommendation-hero-loading"');
    expect(html).toContain("animate-pulse");
  });

  it("renders a clean error state when error message provided", () => {
    const html = renderToStaticMarkup(
      <RecommendationHero error="Failed to connect to INCOIS THREDDS telemetry" />
    );
    expect(html).toContain('data-testid="recommendation-hero-error"');
    expect(html).toContain("Failed to connect to INCOIS THREDDS telemetry");
  });

  it("renders a polished empty state when risk is null", () => {
    const html = renderToStaticMarkup(<RecommendationHero risk={null} />);
    expect(html).toContain('data-testid="recommendation-hero-empty"');
    expect(html).toContain("Select a coastal coordinate or enter a query");
  });
});
