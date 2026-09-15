import { describe, it, expect, vi, afterEach } from "vitest";
import { parseSSEChunk, streamChat, fetchHistory } from "./chatClient";

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

    const gen = streamChat("session-1", "hello");
    await expect(gen.next()).rejects.toThrow("/chat failed: 500");
  });
});

describe("fetchHistory", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed history on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => [{ role: "user", content: "hi" }],
      })
    );

    const history = await fetchHistory("session-1");
    expect(history).toEqual([{ role: "user", content: "hi" }]);
  });

  it("throws when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 404 })
    );

    await expect(fetchHistory("session-1")).rejects.toThrow(
      "/sessions/session-1/history failed: 404"
    );
  });
});
