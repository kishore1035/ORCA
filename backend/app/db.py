"""Persistent per-session chat history.

SQLite, not the spec's literal "Postgres" -- zero-config, file-based, free,
no server process to run or deploy, which matters for a hackathon demo.
This is deliberate persistent history, not real multi-user accounts: a
"session" is just whatever session_id the client holds (crypto.randomUUID(),
generated once and cached in localStorage) -- there is no login/auth, and
anyone who knows a session_id can read its history. Real accounts stay
explicitly out of scope.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "orca.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_lat REAL,
                last_lon REAL,
                last_verdict TEXT
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
        conn.commit()
    finally:
        conn.close()


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
