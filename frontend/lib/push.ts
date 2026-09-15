// Real Web Push subscription (browser -> browser vendor's push service,
// e.g. Chrome -> Google, no third party). Complements lib/voice.ts and
// chatClient.subscribeToAlerts: that SSE stream only delivers while a tab
// is open; this reaches the user via a service worker even with no tab
// open, as long as they've opted in once and the browser/OS push service
// is willing to deliver (best-effort, like any push system).
//
// Uses globalThis rather than navigator/window directly, same reasoning as
// voice.ts: this project's test environment has no DOM, so globalThis is
// what's actually testable without adding jsdom.
import { fetchVapidPublicKey, subscribePush } from "./chatClient";

interface MinimalPushSubscription {
  toJSON(): PushSubscriptionJSON;
}

interface MinimalPushManager {
  subscribe(options: { userVisibleOnly: boolean; applicationServerKey: Uint8Array }): Promise<MinimalPushSubscription>;
}

interface MinimalServiceWorkerRegistration {
  pushManager: MinimalPushManager;
}

interface MinimalServiceWorkerContainer {
  register(url: string): Promise<MinimalServiceWorkerRegistration>;
}

interface MinimalNotification {
  requestPermission(): Promise<string>;
}

function getGlobal(): Record<string, unknown> {
  return globalThis as unknown as Record<string, unknown>;
}

export function isPushSupported(): boolean {
  const g = getGlobal();
  return Boolean(g.navigator && (g.navigator as { serviceWorker?: unknown }).serviceWorker && g.PushManager);
}

// PushManager requires the VAPID key as a raw Uint8Array, but the server
// hands it over base64url-encoded (see push.get_vapid_public_key_b64) --
// this is the standard conversion, not a project-specific format.
function urlBase64ToUint8Array(base64: string): Uint8Array {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const normalized = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(normalized);
  return Uint8Array.from(rawData, (char) => char.charCodeAt(0));
}

/**
 * Registers the service worker, requests notification permission, subscribes
 * via PushManager, and sends the subscription to the backend. Throws if the
 * browser doesn't support push or the user denies permission.
 */
export async function subscribeToPush(sessionId: string, token: string): Promise<void> {
  if (!isPushSupported()) throw new Error("Push notifications are not supported in this browser");

  const g = getGlobal();
  const notification = g.Notification as MinimalNotification | undefined;
  if (notification) {
    const permission = await notification.requestPermission();
    if (permission !== "granted") throw new Error("Notification permission was not granted");
  }

  const serviceWorker = (g.navigator as { serviceWorker: MinimalServiceWorkerContainer }).serviceWorker;
  const registration = await serviceWorker.register("/sw.js");

  const publicKey = await fetchVapidPublicKey();
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(publicKey),
  });

  await subscribePush(sessionId, token, subscription.toJSON());
}
