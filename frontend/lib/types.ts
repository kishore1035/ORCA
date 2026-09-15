export interface TraceEntry {
  agent: string;
  inputs: Record<string, unknown>;
  output: Record<string, unknown>;
  sources: string[];
  fetched_at: string | null;
  is_cached: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export type ChatStreamEvent =
  | { type: "trace"; data: TraceEntry }
  | { type: "answer"; data: { answer: string } };

export interface ProactiveAlert {
  type: "alert";
  verdict: string;
  reasons: string[];
  lat: number;
  lon: number;
}

export interface RouteWaypoint {
  lat: number;
  lon: number;
  verdict: string;
  reasons: string[];
}

export interface AuthResponse {
  token: string;
  user_id: number;
  email: string;
}
