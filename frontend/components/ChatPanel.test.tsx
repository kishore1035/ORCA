import { describe, it, expect, vi } from "vitest";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ChatPanel } from "./ChatPanel";
import { ChatMessage } from "@/lib/types";

describe("ChatPanel", () => {
  it("renders empty state with helpful introductory prompt when no messages", () => {
    const html = renderToStaticMarkup(
      <ChatPanel messages={[]} onSend={vi.fn()} isStreaming={false} />
    );
    expect(html).toContain("ORCA Marine Reasoning Assistant");
    expect(html).toContain("Verified Demo Scenarios");
  });

  it("differentiates a clarifying/follow-up question visually with distinct badge", () => {
    const messages: ChatMessage[] = [
      {
        role: "assistant",
        content: "I need a location to answer that -- which coast, port, or coordinates should I check?",
      },
    ];
    const html = renderToStaticMarkup(
      <ChatPanel messages={messages} onSend={vi.fn()} isStreaming={false} />
    );
    expect(html).toContain("Location / Query Clarification Needed");
    expect(html).toContain("Quick select:");
    expect(html).toContain("Mangaluru Coast");
  });

  it("differentiates an error message visually with warning treatment", () => {
    const messages: ChatMessage[] = [
      {
        role: "assistant",
        content: "Unable to complete marine telemetry analysis. Could not connect to INCOIS feeds.",
        is_error: true,
      },
    ];
    const html = renderToStaticMarkup(
      <ChatPanel messages={messages} onSend={vi.fn()} isStreaming={false} />
    );
    expect(html).toContain("Telemetry Processing Notice");
    expect(html).toContain("Unable to complete marine telemetry analysis");
  });

  it("renders a successful answer with synthesized marine advisory badge", () => {
    const messages: ChatMessage[] = [
      {
        role: "assistant",
        content: "Conditions near Mangaluru are favorable for coastal departure with significant wave height at 1.2m.",
        risk: {
          risk_score: 18,
          risk_level: "LOW",
          factors: ["Wave height 1.2m normal"],
          recommendation: "Safe to depart at 06:00",
          confidence: 0.94,
        },
      },
    ];
    const html = renderToStaticMarkup(
      <ChatPanel messages={messages} onSend={vi.fn()} isStreaming={false} />
    );
    expect(html).toContain("Synthesized Marine Advisory");
    expect(html).toContain("Safe to depart at 06:00");
  });

  it("renders the loading typing indicator and agent status when isStreaming is true", () => {
    const html = renderToStaticMarkup(
      <ChatPanel
        messages={[]}
        onSend={vi.fn()}
        isStreaming={true}
        currentTrace={[
          {
            agent: "weather",
            inputs: {},
            output: {},
            sources: ["INCOIS"],
            fetched_at: null,
            is_cached: false,
          },
        ]}
      />
    );
    expect(html).toContain("Weather agent fetching INCOIS ocean forecast &amp; IMD warnings...");
    expect(html).toContain("animate-wave-dot-1");
  });
});
