from httpx import AsyncClient, ASGITransport
from app import auth, db, push
from app import main as main_module


def _auth_headers(user_id: int = 1, email: str = "fisher@example.com") -> dict:
    token = auth.create_token(user_id, email)
    return {"Authorization": f"Bearer {token}"}


async def test_vapid_public_key_endpoint_returns_a_key(tmp_path, monkeypatch):
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY_PATH", tmp_path / "vapid.pem")

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/push/vapid-public-key")

    assert response.status_code == 200
    assert len(response.json()["public_key"]) > 40


async def test_push_subscribe_stores_subscription(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/push/subscribe",
            json={
                "session_id": "s1",
                "subscription": {"endpoint": "https://push.example.com/x", "keys": {"p256dh": "a", "auth": "b"}},
            },
            headers=_auth_headers(user_id=1),
        )

    assert response.status_code == 200
    subs = db.get_push_subscriptions("s1")
    assert len(subs) == 1
    assert subs[0]["endpoint"] == "https://push.example.com/x"


async def test_push_subscribe_rejects_missing_token(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/push/subscribe",
            json={"session_id": "s1", "subscription": {"endpoint": "https://push.example.com/x"}},
        )

    assert response.status_code == 401


async def test_push_subscribe_rejects_other_users_session(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.ensure_session("s1", user_id=999)

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/push/subscribe",
            json={"session_id": "s1", "subscription": {"endpoint": "https://push.example.com/x"}},
            headers=_auth_headers(user_id=1),
        )

    assert response.status_code == 403
