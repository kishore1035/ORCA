import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app import db
from app.config import get_settings
from app.llm import get_llm_client
from app.graph import build_graph
from app.schemas import ChatMessage, ChatRequest

app = FastAPI(title="ORCA Marine Intelligence Platform")

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/sessions/{session_id}/history")
async def session_history(session_id: str) -> list[ChatMessage]:
    return [ChatMessage(**m) for m in db.get_history(session_id)]


@app.post("/chat")
async def chat(request: ChatRequest):
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
                yield f"event: trace\ndata: {entry.model_dump_json()}\n\n"
            last_trace_len = len(trace)
            if state.get("final_answer"):
                db.append_message(request.session_id, "assistant", state["final_answer"])
                payload = json.dumps({"answer": state["final_answer"]})
                yield f"event: answer\ndata: {payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
