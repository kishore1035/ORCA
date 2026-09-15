import { describe, it, expect, vi, afterEach } from "vitest";
import * as chatClient from "./chatClient";
import { isPushSupported, subscribeToPush } from "./push";

describe("isPushSupported", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns false when navigator.serviceWorker is missing", () => {
    vi.stubGlobal("navigator", {});
    vi.stubGlobal("PushManager", class {});
    expect(isPushSupported()).toBe(false);
  });

  it("returns false when PushManager is missing", () => {
    vi.stubGlobal("navigator", { serviceWorker: {} });
    expect(isPushSupported()).toBe(false);
  });

  it("returns true when both are present", () => {
    vi.stubGlobal("navigator", { serviceWorker: {} });
    vi.stubGlobal("PushManager", class {});
    expect(isPushSupported()).toBe(true);
  });
});

describe("subscribeToPush", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("throws when push is unsupported", async () => {
    vi.stubGlobal("navigator", {});
    await expect(subscribeToPush("session-1", "token-1")).rejects.toThrow("not supported");
  });

  it("throws when notification permission is denied", async () => {
    vi.stubGlobal("navigator", { serviceWorker: {} });
    vi.stubGlobal("PushManager", class {});
    vi.stubGlobal("Notification", { requestPermission: vi.fn().mockResolvedValue("denied") });

    await expect(subscribeToPush("session-1", "token-1")).rejects.toThrow("not granted");
  });

  it("registers the service worker, subscribes, and posts the subscription", async () => {
    const toJSON = vi.fn().mockReturnValue({ endpoint: "https://push.example.com/x" });
    const pushManager = { subscribe: vi.fn().mockResolvedValue({ toJSON }) };
    const register = vi.fn().mockResolvedValue({ pushManager });

    vi.stubGlobal("navigator", { serviceWorker: { register } });
    vi.stubGlobal("PushManager", class {});
    vi.stubGlobal("Notification", { requestPermission: vi.fn().mockResolvedValue("granted") });

    vi.spyOn(chatClient, "fetchVapidPublicKey").mockResolvedValue("BBBB");
    const subscribePushSpy = vi.spyOn(chatClient, "subscribePush").mockResolvedValue(undefined);

    await subscribeToPush("session-1", "token-1");

    expect(register).toHaveBeenCalledWith("/sw.js");
    expect(pushManager.subscribe).toHaveBeenCalledOnce();
    expect(subscribePushSpy).toHaveBeenCalledWith("session-1", "token-1", { endpoint: "https://push.example.com/x" });
  });
});
