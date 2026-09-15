import json
import pytest
from pathlib import Path
from app.connectors.base import fetch_with_fallback


async def test_live_fetch_success_returns_live_data():
    async def live_fetch():
        return {"value": 42}

    result = await fetch_with_fallback("test-source", live_fetch, Path("unused.json"))
    assert result.is_cached is False
    assert result.data == {"value": 42}
    assert result.source == "test-source"


async def test_falls_back_to_snapshot_after_two_failures(tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps({
        "fetched_at": "2026-09-01T06:00:00+00:00",
        "data": {"value": "cached"},
    }))
    call_count = 0

    async def failing_fetch():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("boom")

    result = await fetch_with_fallback("test-source", failing_fetch, snapshot_path)
    assert call_count == 2, "must retry exactly once before falling back"
    assert result.is_cached is True
    assert result.data == {"value": "cached"}
    assert result.source == "test-source"
