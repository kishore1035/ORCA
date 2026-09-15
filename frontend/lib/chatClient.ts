import { ChatMessage, ChatStreamEvent } from "./types";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

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

export async function fetchHistory(sessionId: string): Promise<ChatMessage[]> {
  const response = await fetch(`${BACKEND_URL}/sessions/${sessionId}/history`);
  if (!response.ok) throw new Error(`/sessions/${sessionId}/history failed: ${response.status}`);
  return response.json();
}

export async function* streamChat(
  sessionId: string,
  message: string
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
