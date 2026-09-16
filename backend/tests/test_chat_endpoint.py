from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app import auth, db
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


class FakeGraphWithGeospatial:
    async def astream(self, input, stream_mode):
        geo_entry = TraceEntry(
            agent="geospatial", inputs={}, output={"lat": 9.9679, "lon": 76.2444},
            sources=["test"], fetched_at=datetime.now(timezone.utc), is_cached=False,
        )
        yield {"trace": [geo_entry]}
        yield {"trace": [geo_entry], "final_answer": "Kochi is safe."}


def _auth_headers(user_id: int = 1, email: str = "fisher@example.com") -> dict:
    token = auth.create_token(user_id, email)
    return {"Authorization": f"Bearer {token}"}


async def test_chat_endpoint_streams_trace_then_answer(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    monkeypatch.setattr(main_module, "build_graph", lambda client: FakeGraph())
    monkeypatch.setattr(main_module, "get_llm_client", lambda: object())

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST", "/chat", json={"session_id": "s1", "message": "is it safe?"},
            headers=_auth_headers(),
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
            "POST", "/chat", json={"session_id": "s2", "message": "is it safe?"},
            headers=_auth_headers(),
        ) as response:
            async for _ in response.aiter_text():
                pass

    assert db.get_history("s2") == [
        {"role": "user", "content": "is it safe?"},
        {"role": "assistant", "content": "It is safe to go out."},
    ]


async def test_chat_endpoint_allows_missing_token_as_guest(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    monkeypatch.setattr(main_module, "build_graph", lambda client: FakeGraph())
    monkeypatch.setattr(main_module, "get_llm_client", lambda: object())

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/chat", json={"session_id": "s1", "message": "hi"})

    assert response.status_code == 200
    assert db.get_session_owner("s1") is None


async def test_chat_endpoint_rejects_invalid_token(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    monkeypatch.setattr(main_module, "build_graph", lambda client: FakeGraph())
    monkeypatch.setattr(main_module, "get_llm_client", lambda: object())

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat",
            json={"session_id": "s1", "message": "hi"},
            headers={"Authorization": "Bearer not-a-real-token"},
        )

    assert response.status_code == 401


async def test_chat_endpoint_rejects_session_owned_by_another_user(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    monkeypatch.setattr(main_module, "build_graph", lambda client: FakeGraph())
    monkeypatch.setattr(main_module, "get_llm_client", lambda: object())
    db.ensure_session("someone-elses-session", user_id=999)

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/chat", json={"session_id": "someone-elses-session", "message": "hi"},
            headers=_auth_headers(user_id=1),
        )

    assert response.status_code == 403


async def test_session_history_endpoint_returns_persisted_messages(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.ensure_session("s3", user_id=1)
    db.append_message("s3", "user", "hello")
    db.append_message("s3", "assistant", "hi there")

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/sessions/s3/history", headers=_auth_headers(user_id=1))

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
        response = await client.get("/sessions/never-seen/history", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json() == []


async def test_session_history_endpoint_allows_missing_token_for_unowned_session(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/sessions/s3/history")

    assert response.status_code == 200


async def test_session_history_endpoint_rejects_missing_token_for_owned_session(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.ensure_session("s3", user_id=999)

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/sessions/s3/history")

    assert response.status_code == 403


async def test_session_history_endpoint_rejects_other_users_session(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.ensure_session("s3", user_id=999)

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/sessions/s3/history", headers=_auth_headers(user_id=1))

    assert response.status_code == 403


async def test_chat_endpoint_records_last_location_from_geospatial_trace(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    monkeypatch.setattr(main_module, "build_graph", lambda client: FakeGraphWithGeospatial())
    monkeypatch.setattr(main_module, "get_llm_client", lambda: object())

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST", "/chat", json={"session_id": "s6", "message": "is it safe near Kochi?"},
            headers=_auth_headers(),
        ) as response:
            async for _ in response.aiter_text():
                pass

    assert db.get_tracked_sessions() == [{"session_id": "s6", "lat": 9.9679, "lon": 76.2444}]
