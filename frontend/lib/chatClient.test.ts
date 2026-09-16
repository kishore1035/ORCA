import { describe, it, expect, vi, afterEach } from "vitest";
import {
  parseSSEChunk,
  streamChat,
  fetchHistory,
  subscribeToAlerts,
  signup,
  login,
  fetchVapidPublicKey,
  subscribePush,
} from "./chatClient";

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

  it("sends a backend-valid location source (regression: backend rejects 'USER_SELECTED')", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      body: new ReadableStream({
        start(controller) {
          controller.close();
        },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const gen = streamChat("session-1", "hello", "test-token", { lat: 12.87, lon: 74.84 });
    for await (const _ of gen) {
      // drain
    }

    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.location.source).toBe("MANUAL");
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

describe("fetchVapidPublicKey", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the public key on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ public_key: "BBBB" }) })
    );

    expect(await fetchVapidPublicKey()).toBe("BBBB");
  });

  it("throws when the response is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));

    await expect(fetchVapidPublicKey()).rejects.toThrow("/push/vapid-public-key failed: 500");
  });
});

describe("subscribePush", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts the subscription with an auth header", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal("fetch", fetchMock);

    await subscribePush("session-1", "token-1", { endpoint: "https://push.example.com/x" });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/push/subscribe"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({ Authorization: "Bearer token-1" }),
      })
    );
  });

  it("throws when the response is not ok", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403 }));

    await expect(subscribePush("session-1", "token-1", { endpoint: "x" })).rejects.toThrow(
      "/push/subscribe failed: 403"
    );
  });
});
