import time
from app import auth


def test_hash_password_then_verify_succeeds_with_correct_password():
    password_hash, salt = auth.hash_password("correct horse battery staple")
    assert auth.verify_password("correct horse battery staple", password_hash, salt) is True


def test_verify_password_fails_with_wrong_password():
    password_hash, salt = auth.hash_password("correct horse battery staple")
    assert auth.verify_password("wrong password", password_hash, salt) is False


def test_hash_password_uses_a_random_salt_each_time():
    hash1, salt1 = auth.hash_password("same password")
    hash2, salt2 = auth.hash_password("same password")
    assert salt1 != salt2
    assert hash1 != hash2


def test_create_token_then_decode_roundtrips_claims():
    token = auth.create_token(user_id=42, email="fisher@example.com")
    payload = auth.decode_token(token)
    assert payload["user_id"] == 42
    assert payload["email"] == "fisher@example.com"


def test_decode_token_returns_none_for_garbage_token():
    assert auth.decode_token("not-a-real-token") is None


def test_decode_token_returns_none_for_expired_token(monkeypatch):
    monkeypatch.setattr(auth, "TOKEN_TTL_SECONDS", 0)
    token = auth.create_token(user_id=1, email="a@example.com")
    time.sleep(1.1)
    assert auth.decode_token(token) is None
