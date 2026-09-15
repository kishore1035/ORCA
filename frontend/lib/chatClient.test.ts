import { describe, it, expect, vi, afterEach } from "vitest";
import { parseSSEChunk, streamChat, fetchHistory, subscribeToAlerts, signup, login } from "./chatClient";

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

    const gen = streamChat("session-1", "hello", "test-token");
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

    const history = await fetchHistory("session-1", "test-token");
    expect(history).toEqual([{ role: "user", content: "hi" }]);
  });

  it("throws when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 404 })
    );

    await expect(fetchHistory("session-1", "test-token")).rejects.toThrow(
      "/sessions/session-1/history failed: 404"
    );
  });
});

describe("subscribeToAlerts", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("invokes the callback with parsed alert data and closes on unsubscribe", () => {
    const listeners: Record<string, (event: { data: string }) => void> = {};
    const close = vi.fn();
    class FakeEventSource {
      addEventListener(type: string, listener: (event: { data: string }) => void) {
        listeners[type] = listener;
      }
      close = close;
    }
    vi.stubGlobal("EventSource", FakeEventSource);

    const onAlert = vi.fn();
    const unsubscribe = subscribeToAlerts("session-1", "test-token", onAlert);

    listeners["alert"]({ data: JSON.stringify({ type: "alert", verdict: "unsafe", reasons: ["x"], lat: 1, lon: 2 }) });
    expect(onAlert).toHaveBeenCalledWith({ type: "alert", verdict: "unsafe", reasons: ["x"], lat: 1, lon: 2 });

    unsubscribe();
    expect(close).toHaveBeenCalledOnce();
  });
});

describe("signup", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the auth response on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ token: "t1", user_id: 1, email: "a@example.com" }),
      })
    );

    const result = await signup("a@example.com", "password123");
    expect(result).toEqual({ token: "t1", user_id: 1, email: "a@example.com" });
  });

  it("throws the server's error detail on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ detail: "Email already registered" }),
      })
    );

    await expect(signup("a@example.com", "password123")).rejects.toThrow(
      "Email already registered"
    );
  });
});

describe("login", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the auth response on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ token: "t1", user_id: 1, email: "a@example.com" }),
      })
    );

    const result = await login("a@example.com", "password123");
    expect(result).toEqual({ token: "t1", user_id: 1, email: "a@example.com" });
  });

  it("throws the server's error detail on failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Invalid email or password" }),
      })
    );

    await expect(login("a@example.com", "wrong")).rejects.toThrow("Invalid email or password");
  });
});
