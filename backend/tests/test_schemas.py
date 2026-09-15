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


def test_chat_request_parses_history():
    req = ChatRequest(
        session_id="abc",
        message="is it safe tomorrow?",
        history=[ChatMessage(role="user", content="hi")],
    )
    assert req.history[0].role == "user"
