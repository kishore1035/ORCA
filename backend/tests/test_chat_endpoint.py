from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app import main as main_module
from app.schemas import TraceEntry


class FakeGraph:
    async def astream(self, input, stream_mode):
        trace_entry = TraceEntry(
            agent="weather", inputs={}, output={"wave_height_m": 1.0},
            sources=["test"], fetched_at=datetime.now(timezone.utc), is_cached=False,
        )
        yield {"trace": [trace_entry]}
        yield {"trace": [trace_entry], "final_answer": "It is safe to go out."}


async def test_chat_endpoint_streams_trace_then_answer(monkeypatch):
    monkeypatch.setattr(main_module, "build_graph", lambda client: FakeGraph())
    monkeypatch.setattr(main_module, "get_llm_client", lambda: object())

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST", "/chat", json={"session_id": "s1", "message": "is it safe?", "history": []}
        ) as response:
            body = ""
            async for chunk in response.aiter_text():
                body += chunk

    assert "event: trace" in body
    assert "event: answer" in body
    assert "It is safe to go out." in body
