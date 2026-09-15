from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

DataStatus = Literal["LIVE", "FORECAST", "CACHED", "HISTORICAL"]


class ConnectorResult(BaseModel):
    data: Any
    source: str
    fetched_at: datetime
    is_cached: bool
    data_status: DataStatus = "LIVE"


LocationSource = Literal["GPS", "GOOGLE_MAPS", "MAP_CLICK", "MANUAL"]


class CanonicalLocation(BaseModel):
    latitude: float
    longitude: float
    display_name: str | None = None
    district: str | None = None
    state: str | None = None
    country: str = "India"
    source: LocationSource = "MANUAL"
    distance_to_coast_km: float | None = None
    is_offshore: bool = True
    nearest_coastal_point: tuple[float, float] | None = None
    in_marine_coverage: bool = True
    coverage_message: str | None = None


class MarineParameter(BaseModel):
    parameter: str
    value: Any
    unit: str
    latitude: float
    longitude: float
    timestamp: str
    valid_from: str | None = None
    valid_until: str | None = None
    source: str
    data_status: DataStatus = "FORECAST"
    confidence: float = 0.9
    grid_latitude: float | None = None
    grid_longitude: float | None = None
    grid_distance_km: float | None = None


class RiskAssessment(BaseModel):
    risk_score: int  # 0 to 100
    risk_level: Literal["LOW", "MODERATE", "HIGH", "EXTREME"]
    factors: list[str]
    recommendation: str
    confidence: float = 0.85


class VerificationResult(BaseModel):
    is_verified: bool
    sources: list[str]
    data_status: str
    checks_passed: list[str]
    issues: list[str]
    confidence: float = 0.9
    nearest_grid_distance_km: float | None = None


class WhatIfComparison(BaseModel):
    original_time: str
    original_risk_score: int
    original_risk_level: str
    alternative_time: str
    alternative_risk_score: int
    alternative_risk_level: str
    differences: list[dict[str, Any]] = Field(default_factory=list)
    verdict: str
    comparison_type: Literal["time", "location"] = "time"
    original_location: str | None = None
    alternative_location: str | None = None
    spatial_delta_km: float | None = None


class TraceEntry(BaseModel):
    agent: str
    inputs: dict[str, Any]
    output: dict[str, Any]
    sources: list[str]
    fetched_at: datetime | None = None
    is_cached: bool = False


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    location: CanonicalLocation | None = None


class ChatResponse(BaseModel):
    answer: str
    trace: list[TraceEntry]
    geojson: dict[str, Any] | None = None
    risk: RiskAssessment | None = None
    verification: VerificationResult | None = None
    what_if: WhatIfComparison | None = None
    evidence: list[MarineParameter] | None = None
    location: CanonicalLocation | None = None


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    email: str


class PushSubscribeRequest(BaseModel):
    session_id: str
    subscription: dict[str, Any]
