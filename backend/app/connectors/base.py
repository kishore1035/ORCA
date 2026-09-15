import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable
from app.schemas import ConnectorResult


async def fetch_with_fallback(
    source: str,
    live_fetch: Callable[[], Awaitable[Any]],
    snapshot_path: Path,
    timeout_seconds: float = 10.0,
    live_data_status: str = "LIVE",
) -> ConnectorResult:
    for attempt in range(2):
        try:
            data = await asyncio.wait_for(live_fetch(), timeout=timeout_seconds)
            return ConnectorResult(
                data=data,
                source=source,
                fetched_at=datetime.now(timezone.utc),
                is_cached=False,
                data_status=live_data_status,
            )
        except Exception:
            if attempt == 0:
                continue

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    status = snapshot.get("data_status", "CACHED")
    return ConnectorResult(
        data=snapshot["data"],
        source=source,
        fetched_at=datetime.fromisoformat(snapshot["fetched_at"]),
        is_cached=True,
        data_status=status,
    )

