import { describe, it, expect } from "vitest";
import { parseSSEChunk } from "./chatClient";

describe("parseSSEChunk", () => {
  it("parses a trace event", () => {
    const chunk =
      'event: trace\ndata: {"agent":"weather","inputs":{},"output":{},"sources":[],"fetched_at":null,"is_cached":false}\n\n';
    const events = parseSSEChunk(chunk);
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe("trace");
  });

  it("parses an answer event", () => {
    const chunk = 'event: answer\ndata: {"answer":"It is safe to go out."}\n\n';
    const events = parseSSEChunk(chunk);
    expect(events[0]).toEqual({ type: "answer", data: { answer: "It is safe to go out." } });
  });

  it("ignores blocks missing an event or data line", () => {
    expect(parseSSEChunk(": heartbeat\n\n")).toHaveLength(0);
  });
});
