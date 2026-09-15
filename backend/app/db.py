"""Persistent per-session chat history and user accounts.

SQLite, not the spec's literal "Postgres" -- zero-config, file-based, free,
no server process to run or deploy, which matters for a hackathon demo.
Real accounts (see users table / create_user / ensure_session) -- a session
is now owned by exactly one user_id; anonymous sessions are no longer
possible once auth is enforced at the endpoint layer (see app/auth.py and
app/main.py).
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "orca.db"


class DuplicateEmailError(Exception):
    pass


class SessionOwnershipError(Exception):
    pass


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_lat REAL,
                last_lon REAL,
                last_verdict TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                subscription_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )"""
        )
        conn.commit()
    finally:
        conn.close()


def create_user(email: str, password_hash: str, password_salt: str) -> int:
    conn = _connect()
    try:
        try:
            cursor = conn.execute(
                "INSERT INTO users (email, password_hash, password_salt) VALUES (?, ?, ?)",
                (email, password_hash, password_salt),
            )
        except sqlite3.IntegrityError:
            raise DuplicateEmailError(email)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, email, password_hash, password_salt FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    return {"id": row[0], "email": row[1], "password_hash": row[2], "password_salt": row[3]}


def ensure_session(session_id: str, user_id: int) -> None:
    """Creates the session row owned by user_id if it doesn't exist yet.
    Raises SessionOwnershipError if the session already exists under a
    different user -- a session_id is not a shared/guessable credential
    once auth is in place."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (id, user_id) VALUES (?, ?)", (session_id, user_id)
        )
        conn.commit()
        row = conn.execute("SELECT user_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
    finally:
        conn.close()
    if row[0] != user_id:
        raise SessionOwnershipError(session_id)


def get_session_owner(session_id: str) -> int | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT user_id FROM sessions WHERE id = ?", (session_id,)).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def get_history(session_id: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()
    return [{"role": role, "content": content} for role, content in rows]


def append_message(session_id: str, role: str, content: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (id) VALUES (?)", (session_id,)
        )
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        conn.commit()
    finally:
        conn.close()


def set_last_location(session_id: str, lat: float, lon: float) -> None:
    conn = _connect()
    try:
        conn.execute("INSERT OR IGNORE INTO sessions (id) VALUES (?)", (session_id,))
        conn.execute(
            "UPDATE sessions SET last_lat = ?, last_lon = ? WHERE id = ?",
            (lat, lon, session_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_tracked_sessions() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, last_lat, last_lon FROM sessions "
            "WHERE last_lat IS NOT NULL AND last_lon IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()
    return [{"session_id": sid, "lat": lat, "lon": lon} for sid, lat, lon in rows]


def get_last_verdict(session_id: str) -> str | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT last_verdict FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


def set_last_verdict(session_id: str, verdict: str) -> None:
    conn = _connect()
    try:
        conn.execute("INSERT OR IGNORE INTO sessions (id) VALUES (?)", (session_id,))
        conn.execute(
            "UPDATE sessions SET last_verdict = ? WHERE id = ?", (verdict, session_id)
        )
        conn.commit()
    finally:
        conn.close()


def save_push_subscription(session_id: str, subscription_json: str) -> None:
    """Dedupes by endpoint (a browser re-subscribing sends the same
    endpoint again) so this session doesn't accumulate stale duplicates."""
    endpoint = json.loads(subscription_json).get("endpoint")
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, subscription_json FROM push_subscriptions WHERE session_id = ?",
            (session_id,),
        ).fetchall()
        for row_id, existing_json in rows:
            if json.loads(existing_json).get("endpoint") == endpoint:
                conn.execute("DELETE FROM push_subscriptions WHERE id = ?", (row_id,))
        conn.execute(
            "INSERT INTO push_subscriptions (session_id, subscription_json) VALUES (?, ?)",
            (session_id, subscription_json),
        )
        conn.commit()
    finally:
        conn.close()


def get_push_subscriptions(session_id: str) -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT subscription_json FROM push_subscriptions WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()
    return [json.loads(row[0]) for row in rows]
