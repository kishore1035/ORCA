from app import push


def test_get_vapid_public_key_generates_and_persists(tmp_path, monkeypatch):
    key_path = tmp_path / "vapid.pem"
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY_PATH", key_path)

    key1 = push.get_vapid_public_key_b64()
    assert key_path.exists()
    assert isinstance(key1, str) and len(key1) > 40

    # Second call reuses the persisted key rather than generating a new one.
    key2 = push.get_vapid_public_key_b64()
    assert key1 == key2


def test_send_push_returns_true_on_success(tmp_path, monkeypatch):
    key_path = tmp_path / "vapid.pem"
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY_PATH", key_path)
    monkeypatch.setattr(push, "_webpush", lambda **kwargs: None)

    result = push.send_push({"endpoint": "https://example.com/push/x"}, {"title": "Alert"})
    assert result is True


def test_send_push_returns_false_on_webpush_exception(tmp_path, monkeypatch):
    key_path = tmp_path / "vapid.pem"
    monkeypatch.setattr(push, "VAPID_PRIVATE_KEY_PATH", key_path)

    def raise_exc(**kwargs):
        raise push.WebPushException("gone")

    monkeypatch.setattr(push, "_webpush", raise_exc)

    result = push.send_push({"endpoint": "https://example.com/push/x"}, {"title": "Alert"})
    assert result is False
