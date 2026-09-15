from datetime import datetime, timezone
from app.schemas import ConnectorResult, TraceEntry, ChatRequest, ChatMessage


def test_connector_result_roundtrip():
    result = ConnectorResult(
        data={"wave_height_m": 1.2},
        source="open-meteo-marine",
        fetched_at=datetime.now(timezone.utc),
        is_cached=False,
    )
    assert result.is_cached is False
    assert result.data["wave_height_m"] == 1.2


def test_trace_entry_defaults():
    entry = TraceEntry(agent="weather", inputs={}, output={}, sources=["x"])
    assert entry.is_cached is False
    assert entry.fetched_at is None


def test_chat_request_has_no_client_supplied_history():
    # History is server-loaded from the persistent store (app.db) by session_id,
    # not trusted from the client -- ChatRequest deliberately has no history field.
    req = ChatRequest(session_id="abc", message="is it safe tomorrow?")
    assert req.session_id == "abc"
    assert not hasattr(req, "history")


def test_chat_message_roundtrip():
    msg = ChatMessage(role="user", content="hi")
    assert msg.role == "user"
    assert msg.content == "hi"
