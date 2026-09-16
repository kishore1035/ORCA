import { describe, it, expect } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { SstTrendChart } from "./SstTrendChart";

describe("SstTrendChart", () => {
  it("renders a sparkline for a full numeric trend", () => {
    const html = renderToStaticMarkup(
      <SstTrendChart
        trend={[
          { date: "2026-09-10", sst_celsius: 27.1 },
          { date: "2026-09-11", sst_celsius: 27.4 },
          { date: "2026-09-12", sst_celsius: 27.9 },
        ]}
      />
    );
    expect(html).toContain("svg");
  });

  it("does not crash on a null-only trend (masked ERDDAP grid cell, e.g. a near-shore point)", () => {
    expect(() =>
      renderToStaticMarkup(
        <SstTrendChart
          trend={[
            { date: "2026-09-10", sst_celsius: null },
            { date: "2026-09-11", sst_celsius: null },
          ]}
        />
      )
    ).not.toThrow();
  });

  it("filters out null points and still renders when enough real points remain", () => {
    const html = renderToStaticMarkup(
      <SstTrendChart
        trend={[
          { date: "2026-09-10", sst_celsius: null },
          { date: "2026-09-11", sst_celsius: 27.4 },
          { date: "2026-09-12", sst_celsius: 27.9 },
        ]}
      />
    );
    expect(html).toContain("svg");
  });

  it("renders nothing when fewer than two real points remain after filtering", () => {
    const html = renderToStaticMarkup(
      <SstTrendChart
        trend={[
          { date: "2026-09-10", sst_celsius: null },
          { date: "2026-09-11", sst_celsius: 27.4 },
        ]}
      />
    );
    expect(html).toBe("");
  });
});
