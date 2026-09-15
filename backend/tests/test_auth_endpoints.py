from httpx import AsyncClient, ASGITransport
from app import db
from app import main as main_module


async def test_signup_then_login_succeeds(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        signup_resp = await client.post(
            "/auth/signup", json={"email": "fisher@example.com", "password": "correcthorse"}
        )
        assert signup_resp.status_code == 200
        assert signup_resp.json()["email"] == "fisher@example.com"
        assert signup_resp.json()["token"]

        login_resp = await client.post(
            "/auth/login", json={"email": "fisher@example.com", "password": "correcthorse"}
        )
        assert login_resp.status_code == 200
        assert login_resp.json()["email"] == "fisher@example.com"


async def test_login_rejects_wrong_password(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/auth/signup", json={"email": "fisher@example.com", "password": "correcthorse"})
        response = await client.post(
            "/auth/login", json={"email": "fisher@example.com", "password": "wrongpassword"}
        )

    assert response.status_code == 401


async def test_login_rejects_unknown_email(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/login", json={"email": "nobody@example.com", "password": "whatever1"}
        )

    assert response.status_code == 401


async def test_signup_rejects_duplicate_email(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/auth/signup", json={"email": "fisher@example.com", "password": "correcthorse"})
        response = await client.post(
            "/auth/signup", json={"email": "fisher@example.com", "password": "anotherpassword"}
        )

    assert response.status_code == 409


async def test_signup_rejects_short_password(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/signup", json={"email": "fisher@example.com", "password": "short"}
        )

    assert response.status_code == 400


async def test_signup_rejects_invalid_email(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/signup", json={"email": "not-an-email", "password": "correcthorse"}
        )

    assert response.status_code == 400
