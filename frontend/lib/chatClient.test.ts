import { describe, it, expect, vi, afterEach } from "vitest";
import { parseSSEChunk, streamChat } from "./chatClient";

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

describe("streamChat", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("throws when the response is not ok, even if a body is present", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        body: new ReadableStream(),
      })
    );

    const gen = streamChat("session-1", "hello", []);
    await expect(gen.next()).rejects.toThrow("/chat failed: 500");
  });
});
