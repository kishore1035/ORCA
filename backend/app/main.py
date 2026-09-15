import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app import alerting, auth, db, push
from app.config import get_settings
from app.llm import get_llm_client
from app.graph import build_graph
from app.schemas import (
    AuthResponse,
    ChatMessage,
    ChatRequest,
    LoginRequest,
    PushSubscribeRequest,
    SignupRequest,
)

# How often to send an SSE keep-alive comment on the alerts stream so
# intermediate proxies/load balancers don't time out an otherwise-idle
# long-lived connection.
ALERT_STREAM_PING_SECONDS = 15
MIN_PASSWORD_LENGTH = 8


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    task = asyncio.create_task(alerting.run_periodic_checks())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="ORCA Marine Intelligence Platform", lifespan=lifespan)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_user_from_token(token: str | None) -> dict:
    if not token:
        raise HTTPException(status_code=401, detail="Missing auth token")
    payload = auth.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired auth token")
    return payload


def _require_user(authorization: str | None = Header(None)) -> dict:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
    return _require_user_from_token(token)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/signup", response_model=AuthResponse)
async def signup(request: SignupRequest) -> AuthResponse:
    if "@" not in request.email or not request.email.strip():
        raise HTTPException(status_code=400, detail="Invalid email")
    if len(request.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400, detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    password_hash, salt = auth.hash_password(request.password)
    try:
        user_id = db.create_user(request.email, password_hash, salt)
    except db.DuplicateEmailError:
        raise HTTPException(status_code=409, detail="Email already registered")
    token = auth.create_token(user_id, request.email)
    return AuthResponse(token=token, user_id=user_id, email=request.email)


@app.post("/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest) -> AuthResponse:
    user = db.get_user_by_email(request.email)
    if not user or not auth.verify_password(request.password, user["password_hash"], user["password_salt"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth.create_token(user["id"], user["email"])
    return AuthResponse(token=token, user_id=user["id"], email=user["email"])


@app.get("/push/vapid-public-key")
async def vapid_public_key() -> dict:
    return {"public_key": push.get_vapid_public_key_b64()}


@app.post("/push/subscribe")
async def push_subscribe(request: PushSubscribeRequest, user: dict = Depends(_require_user)) -> dict:
    try:
        db.ensure_session(request.session_id, user["user_id"])
    except db.SessionOwnershipError:
        raise HTTPException(status_code=403, detail="Session belongs to another user")
    db.save_push_subscription(request.session_id, json.dumps(request.subscription))
    return {"status": "subscribed"}


@app.get("/sessions/{session_id}/history")
async def session_history(session_id: str, user: dict = Depends(_require_user)) -> list[ChatMessage]:
    owner = db.get_session_owner(session_id)
    if owner is not None and owner != user["user_id"]:
        raise HTTPException(status_code=403, detail="Session belongs to another user")
    return [ChatMessage(**m) for m in db.get_history(session_id)]


@app.get("/sessions/{session_id}/alerts/stream")
async def alerts_stream(session_id: str, token: str = Query(...)):
    user = _require_user_from_token(token)
    owner = db.get_session_owner(session_id)
    if owner is not None and owner != user["user_id"]:
        raise HTTPException(status_code=403, detail="Session belongs to another user")

    queue = alerting.subscribe(session_id)

    async def event_stream():
        try:
            while True:
                try:
                    alert = await asyncio.wait_for(queue.get(), timeout=ALERT_STREAM_PING_SECONDS)
                    yield f"event: alert\ndata: {json.dumps(alert)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            alerting.unsubscribe(session_id, queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/chat")
async def chat(request: ChatRequest, user: dict = Depends(_require_user)):
    try:
        db.ensure_session(request.session_id, user["user_id"])
    except db.SessionOwnershipError:
        raise HTTPException(status_code=403, detail="Session belongs to another user")

    client = get_llm_client()
    graph = build_graph(client)
    history = db.get_history(request.session_id)
    db.append_message(request.session_id, "user", request.message)

    async def event_stream():
        last_trace_len = 0
        async for state in graph.astream(
            {"message": request.message, "history": history}, stream_mode="values"
        ):
            trace = state.get("trace", [])
            for entry in trace[last_trace_len:]:
                if entry.agent == "geospatial" and "lat" in entry.output and "lon" in entry.output:
                    db.set_last_location(request.session_id, entry.output["lat"], entry.output["lon"])
                yield f"event: trace\ndata: {entry.model_dump_json()}\n\n"
            last_trace_len = len(trace)
            if state.get("final_answer"):
                db.append_message(request.session_id, "assistant", state["final_answer"])
                payload = json.dumps({"answer": state["final_answer"]})
                yield f"event: answer\ndata: {payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
