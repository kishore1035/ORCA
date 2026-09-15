export type DataStatus = "LIVE" | "FORECAST" | "CACHED" | "HISTORICAL";

export interface MarineParameter {
  parameter: string;
  value: number | string | null;
  unit: string;
  latitude: number;
  longitude: number;
  timestamp: string;
  valid_from?: string | null;
  valid_until?: string | null;
  source: string;
  data_status: DataStatus;
  confidence: number;
  grid_distance_km?: number | null;
}

export interface RiskAssessment {
  risk_score: number;
  risk_level: "LOW" | "MODERATE" | "HIGH" | "EXTREME";
  factors: string[];
  recommendation: string;
  confidence: number;
}

export interface VerificationResult {
  is_verified: boolean;
  sources: string[];
  data_status: string;
  checks_passed: string[];
  issues: string[];
  confidence: number;
}

export interface WhatIfDifference {
  parameter: string;
  original: string;
  alternative: string;
  delta: string;
  impact: string;
}

export interface WhatIfComparison {
  original_time: string;
  original_risk_score: number;
  original_risk_level: string;
  alternative_time: string;
  alternative_risk_score: number;
  alternative_risk_level: string;
  differences: WhatIfDifference[];
  verdict: string;
}

export interface TraceEntry {
  agent: string;
  inputs: Record<string, unknown>;
  output: Record<string, unknown>;
  sources: string[];
  fetched_at: string | null;
  is_cached: boolean;
}

export interface CanonicalLocation {
  latitude?: number;
  longitude?: number;
  lat?: number;
  lon?: number;
  display_name?: string | null;
  district?: string | null;
  state?: string | null;
  country?: string | null;
  source?: string | null;
  distance_to_coast_km?: number | null;
  is_offshore?: boolean;
  nearest_coastal_name?: string | null;
  nearest_coastal_sector?: string | null;
  nearest_coastal_point?: [number, number] | null;
  in_marine_coverage?: boolean;
  coverage_message?: string | null;
  grid_distance_km?: number | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  risk?: RiskAssessment | null;
  verification?: VerificationResult | null;
  what_if?: WhatIfComparison | null;
  evidence?: MarineParameter[] | null;
  location?: CanonicalLocation | null;
}

export type ChatStreamEvent =
  | { type: "trace"; data: TraceEntry }
  | {
      type: "answer";
      data: {
        answer: string;
        risk?: RiskAssessment | null;
        verification?: VerificationResult | null;
        what_if?: WhatIfComparison | null;
        evidence?: MarineParameter[] | null;
        location?: CanonicalLocation | null;
      };
    };

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

