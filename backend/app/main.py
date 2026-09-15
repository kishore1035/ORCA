import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.config import get_settings
from app.llm import get_llm_client
from app.graph import build_graph
from app.schemas import ChatRequest

app = FastAPI(title="ORCA Marine Intelligence Platform")

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


@app.post("/chat")
async def chat(request: ChatRequest):
    client = get_llm_client()
    graph = build_graph(client)
    history = [{"role": m.role, "content": m.content} for m in request.history]

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
                payload = json.dumps({"answer": state["final_answer"]})
                yield f"event: answer\ndata: {payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
