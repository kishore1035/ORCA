import json
from datetime import datetime
from pathlib import Path
from app.schemas import ConnectorResult

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots" / "alerts.json"


async def get_alerts(lat: float, lon: float) -> ConnectorResult:
    """No free live cyclone/lightning feed is wired up for Phase 1 (spec section 3).
    Always serves the cached snapshot; the interface matches every other connector
    so a live feed can be substituted later without touching callers."""
    snapshot = json.loads(SNAPSHOT_PATH.read_text())
    return ConnectorResult(
        data=snapshot["data"],
        source="cached-alerts-snapshot",
        fetched_at=datetime.fromisoformat(snapshot["fetched_at"]),
        is_cached=True,
    )
