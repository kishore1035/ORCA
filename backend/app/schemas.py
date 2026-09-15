from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel


class ConnectorResult(BaseModel):
    data: Any
    source: str
    fetched_at: datetime
    is_cached: bool


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


class ChatResponse(BaseModel):
    answer: str
    trace: list[TraceEntry]
    geojson: dict[str, Any] | None = None


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
