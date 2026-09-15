import { AuthResponse, ChatMessage, ChatStreamEvent, ProactiveAlert } from "./types";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

async function _parseAuthResponse(response: Response, failureLabel: string): Promise<AuthResponse> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? `${failureLabel} failed: ${response.status}`);
  }
  return response.json();
}

export async function signup(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${BACKEND_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return _parseAuthResponse(response, "Signup");
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${BACKEND_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  return _parseAuthResponse(response, "Login");
}

export function parseSSEChunk(chunk: string): ChatStreamEvent[] {
  const events: ChatStreamEvent[] = [];
  const blocks = chunk.split("\n\n").filter((b) => b.trim().length > 0);
  for (const block of blocks) {
    const lines = block.split("\n");
    const eventLine = lines.find((l) => l.startsWith("event: "));
    const dataLine = lines.find((l) => l.startsWith("data: "));
    if (!eventLine || !dataLine) continue;
    const type = eventLine.slice("event: ".length).trim();
    const data = JSON.parse(dataLine.slice("data: ".length));
    if (type === "trace") events.push({ type: "trace", data });
    else if (type === "answer") events.push({ type: "answer", data });
  }
  return events;
}

export async function fetchVapidPublicKey(): Promise<string> {
  const response = await fetch(`${BACKEND_URL}/push/vapid-public-key`);
  if (!response.ok) throw new Error(`/push/vapid-public-key failed: ${response.status}`);
  const body = await response.json();
  return body.public_key;
}

export async function subscribePush(
  sessionId: string,
  token: string,
  subscription: PushSubscriptionJSON
): Promise<void> {
  const response = await fetch(`${BACKEND_URL}/push/subscribe`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ session_id: sessionId, subscription }),
  });
  if (!response.ok) throw new Error(`/push/subscribe failed: ${response.status}`);
}

export async function fetchHistory(sessionId: string, token: string): Promise<ChatMessage[]> {
  const response = await fetch(`${BACKEND_URL}/sessions/${sessionId}/history`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error(`/sessions/${sessionId}/history failed: ${response.status}`);
  return response.json();
}

/**
 * Subscribes to proactive hazard alerts for a session over a long-lived SSE
 * connection -- this delivers alerts while a tab is open. For delivery with
 * no tab open, see lib/push.ts's real Web Push subscription (separate,
 * opt-in, requires the browser to support it).
 * Returns an unsubscribe function.
 */
export function subscribeToAlerts(
  sessionId: string,
  token: string,
  onAlert: (alert: ProactiveAlert) => void
): () => void {
  const url = `${BACKEND_URL}/sessions/${sessionId}/alerts/stream?token=${encodeURIComponent(token)}`;
  const source = new EventSource(url);
  source.addEventListener("alert", (event) => {
    onAlert(JSON.parse((event as MessageEvent).data));
  });
  return () => source.close();
}

export async function* streamChat(
  sessionId: string,
  message: string,
  token: string
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!response.ok) throw new Error(`/chat failed: ${response.status}`);
  if (!response.body) throw new Error("No response body from /chat");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      for (const event of parseSSEChunk(part + "\n\n")) {
        yield event;
      }
    }
  }
}
