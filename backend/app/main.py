import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app import alerting, db
from app.config import get_settings
from app.llm import get_llm_client
from app.graph import build_graph
from app.schemas import ChatMessage, ChatRequest

# How often to send an SSE keep-alive comment on the alerts stream so
# intermediate proxies/load balancers don't time out an otherwise-idle
# long-lived connection.
ALERT_STREAM_PING_SECONDS = 15


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


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/sessions/{session_id}/history")
async def session_history(session_id: str) -> list[ChatMessage]:
    return [ChatMessage(**m) for m in db.get_history(session_id)]


@app.get("/sessions/{session_id}/alerts/stream")
async def alerts_stream(session_id: str):
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
async def chat(request: ChatRequest):
    client = get_llm_client()
    graph = build_graph(client)
    history = db.get_history(request.session_id)
    db.append_message(request.session_id, "user", request.message)

    async def event_stream():
        last_trace_len = 0
        graph_input = {
            "message": request.message,
            "history": history,
            "location": request.location.model_dump() if request.location else None,
        }
        async for state in graph.astream(graph_input, stream_mode="values"):
            trace = state.get("trace", [])
            for entry in trace[last_trace_len:]:
                if entry.agent == "geospatial" and "lat" in entry.output and "lon" in entry.output:
                    db.set_last_location(request.session_id, entry.output["lat"], entry.output["lon"])
                yield f"event: trace\ndata: {entry.model_dump_json()}\n\n"
            last_trace_len = len(trace)
            if state.get("final_answer"):
                db.append_message(request.session_id, "assistant", state["final_answer"])
                payload = json.dumps({
                    "answer": state["final_answer"],
                    "risk": state.get("risk_result"),
                    "verification": state.get("verification_result"),
                    "what_if": state.get("what_if_result"),
                    "evidence": state.get("evidence"),
                    "location": state.get("canonical_location"),
                })
                yield f"event: answer\ndata: {payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

