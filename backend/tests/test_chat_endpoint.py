from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app import db
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


async def test_chat_endpoint_streams_trace_then_answer(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    monkeypatch.setattr(main_module, "build_graph", lambda client: FakeGraph())
    monkeypatch.setattr(main_module, "get_llm_client", lambda: object())

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST", "/chat", json={"session_id": "s1", "message": "is it safe?"}
        ) as response:
            body = ""
            async for chunk in response.aiter_text():
                body += chunk

    assert "event: trace" in body
    assert "event: answer" in body
    assert "It is safe to go out." in body


async def test_chat_endpoint_persists_user_message_and_answer(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    monkeypatch.setattr(main_module, "build_graph", lambda client: FakeGraph())
    monkeypatch.setattr(main_module, "get_llm_client", lambda: object())

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST", "/chat", json={"session_id": "s2", "message": "is it safe?"}
        ) as response:
            async for _ in response.aiter_text():
                pass

    assert db.get_history("s2") == [
        {"role": "user", "content": "is it safe?"},
        {"role": "assistant", "content": "It is safe to go out."},
    ]


async def test_session_history_endpoint_returns_persisted_messages(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.append_message("s3", "user", "hello")
    db.append_message("s3", "assistant", "hi there")

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/sessions/s3/history")

    assert response.status_code == 200
    assert response.json() == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]


async def test_session_history_endpoint_returns_empty_for_new_session(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/sessions/never-seen/history")

    assert response.status_code == 200
    assert response.json() == []
