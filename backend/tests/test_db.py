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
