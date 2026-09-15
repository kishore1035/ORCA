import pytest
from app import db


def test_get_history_returns_empty_list_for_new_session(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    history = db.get_history("new-session")
    assert history == []


def test_append_message_then_get_history_returns_in_order(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    db.append_message("s1", "user", "is it safe?")
    db.append_message("s1", "assistant", "Yes, it is safe.")

    history = db.get_history("s1")
    assert history == [
        {"role": "user", "content": "is it safe?"},
        {"role": "assistant", "content": "Yes, it is safe."},
    ]


def test_history_is_isolated_per_session(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    db.append_message("session-a", "user", "message for a")
    db.append_message("session-b", "user", "message for b")

    assert db.get_history("session-a") == [{"role": "user", "content": "message for a"}]
    assert db.get_history("session-b") == [{"role": "user", "content": "message for b"}]


def test_append_message_creates_db_file_if_missing(tmp_path, monkeypatch):
    db_path = tmp_path / "nested" / "test.db"
    monkeypatch.setattr(db, "DB_PATH", db_path)
    db.init_db()

    assert db_path.exists()


def test_set_last_location_then_get_tracked_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    db.set_last_location("s1", 9.9679, 76.2444)
    tracked = db.get_tracked_sessions()

    assert tracked == [{"session_id": "s1", "lat": 9.9679, "lon": 76.2444}]


def test_get_tracked_sessions_excludes_sessions_without_location(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    db.append_message("no-location-session", "user", "hi")
    tracked = db.get_tracked_sessions()

    assert tracked == []


def test_set_last_location_overwrites_previous_value(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    db.set_last_location("s1", 9.0, 76.0)
    db.set_last_location("s1", 10.0, 77.0)

    tracked = db.get_tracked_sessions()
    assert tracked == [{"session_id": "s1", "lat": 10.0, "lon": 77.0}]


def test_last_verdict_round_trip_defaults_to_none(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    db.set_last_location("s1", 9.0, 76.0)
    assert db.get_last_verdict("s1") is None

    db.set_last_verdict("s1", "unsafe")
    assert db.get_last_verdict("s1") == "unsafe"


def test_create_user_then_get_user_by_email(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    user_id = db.create_user("fisher@example.com", "hash123", "salt456")
    user = db.get_user_by_email("fisher@example.com")

    assert user["id"] == user_id
    assert user["email"] == "fisher@example.com"
    assert user["password_hash"] == "hash123"
    assert user["password_salt"] == "salt456"


def test_get_user_by_email_returns_none_for_unknown_email(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    assert db.get_user_by_email("nobody@example.com") is None


def test_create_user_rejects_duplicate_email(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    db.create_user("fisher@example.com", "hash1", "salt1")
    with pytest.raises(db.DuplicateEmailError):
        db.create_user("fisher@example.com", "hash2", "salt2")


def test_ensure_session_creates_new_session_owned_by_user(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    db.ensure_session("s1", user_id=42)
    assert db.get_session_owner("s1") == 42


def test_ensure_session_is_idempotent_for_same_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    db.ensure_session("s1", user_id=42)
    db.ensure_session("s1", user_id=42)  # second message in the same session
    assert db.get_session_owner("s1") == 42


def test_ensure_session_rejects_wrong_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    db.ensure_session("s1", user_id=42)
    with pytest.raises(db.SessionOwnershipError):
        db.ensure_session("s1", user_id=99)


def test_get_session_owner_returns_none_for_unknown_session(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

    assert db.get_session_owner("never-seen") is None
