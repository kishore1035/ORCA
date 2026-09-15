import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path
import httpx
from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots"
CYCLONE_SNAPSHOT = DATA_DIR / "cyclone_alerts.json"
LIGHTNING_SNAPSHOT = DATA_DIR / "lightning_alerts.json"

GDACS_EVENTS_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH"

# Tropical cyclones affect a wide hazard field (gale-force winds, heavy swell) well
# beyond their tracked center point; this is a coastal-safety-relevant radius, not
# an official meteorological warning-area definition.
CYCLONE_RELEVANCE_RADIUS_KM = 500.0
EARTH_RADIUS_KM = 6371.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


async def _fetch_cyclone_alerts_live(lat: float, lon: float) -> dict:
    from_date = (date.today() - timedelta(days=2)).isoformat()
    to_date = (date.today() + timedelta(days=5)).isoformat()
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            GDACS_EVENTS_URL,
            params={
                "eventtypes": "TC",
                "alertlevel": "Green;Orange;Red",
                "fromDate": from_date,
                "toDate": to_date,
            },
        )
        resp.raise_for_status()
        payload = resp.json()

    cyclone_alerts = []
    for feature in payload.get("features", []):
        props = feature["properties"]
        if props.get("eventtype") != "TC" or props.get("iscurrent") != "true":
            continue
        event_lon, event_lat = feature["geometry"]["coordinates"]
        distance_km = _haversine_km(lat, lon, event_lat, event_lon)
        if distance_km > CYCLONE_RELEVANCE_RADIUS_KM:
            continue
        cyclone_alerts.append(
            {
                "name": props["name"],
                "alertlevel": props["alertlevel"],
                "distance_km": round(distance_km, 1),
                "from": props["fromdate"],
                "to": props["todate"],
            }
        )
    return {"cyclone_alerts": cyclone_alerts}


async def get_cyclone_alerts(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback(
        "gdacs-cyclone-tracker", lambda: _fetch_cyclone_alerts_live(lat, lon), CYCLONE_SNAPSHOT
    )


async def get_lightning_alerts(lat: float, lon: float) -> ConnectorResult:
    """No free live lightning feed is wired up for Phase 1 (spec section 3) --
    Blitzortung, the usual free community network, requires an authenticated
    websocket rather than a simple REST endpoint. Always serves the cached
    snapshot; the interface matches every other connector so a live feed can be
    substituted later without touching callers."""
    snapshot = json.loads(LIGHTNING_SNAPSHOT.read_text())
    return ConnectorResult(
        data=snapshot["data"],
        source="cached-lightning-snapshot",
        fetched_at=datetime.fromisoformat(snapshot["fetched_at"]),
        is_cached=True,
    )
