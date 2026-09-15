import asyncio
import json
import math
import time
from datetime import date, datetime, timedelta
from pathlib import Path
import httpx
import paho.mqtt.client as mqtt
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

# Public, unauthenticated MQTT bridge that republishes Blitzortung.org's
# real-time lightning-strike feed as plain JSON. The raw Blitzortung websocket
# obfuscates its payload with a proprietary compression scheme; this broker
# (run by the maintainer of the Home Assistant Blitzortung integration)
# already does that decoding server-side, so no reverse-engineering is needed
# here -- see https://github.com/mrk-its/homeassistant-blitzortung.
BLITZORTUNG_MQTT_HOST = "blitzortung.ha.sed.pl"
BLITZORTUNG_MQTT_PORT = 1883
GEOHASH_PRECISION = 2
LIGHTNING_RADIUS_KM = 300.0
LIGHTNING_LISTEN_SECONDS = 5.0
_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


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


def _geohash_encode(lat: float, lon: float, precision: int) -> str:
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    geohash = []
    bit = 0
    even = True
    ch = 0
    while len(geohash) < precision:
        if even:
            mid = (lon_range[0] + lon_range[1]) / 2
            if lon > mid:
                ch |= 1 << (4 - bit)
                lon_range[0] = mid
            else:
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat > mid:
                ch |= 1 << (4 - bit)
                lat_range[0] = mid
            else:
                lat_range[1] = mid
        even = not even
        if bit < 4:
            bit += 1
        else:
            geohash.append(_BASE32[ch])
            bit = 0
            ch = 0
    return "".join(geohash)


def _tile_prefixes(lat: float, lon: float, radius_km: float, precision: int) -> set[str]:
    """Geohash tile prefixes covering a point plus its 8 compass-direction
    neighbors at radius_km -- a simple approximation of the true set of tiles
    overlapping a radius-km circle (good enough to avoid the common case of
    missing a strike right at a tile boundary; not an exhaustive bbox-overlap
    search)."""
    km_per_deg_lat = 111.0
    prefixes = {_geohash_encode(lat, lon, precision)}
    for bearing_deg in range(0, 360, 45):
        bearing = math.radians(bearing_deg)
        dlat = (radius_km / km_per_deg_lat) * math.cos(bearing)
        dlon = (radius_km / (km_per_deg_lat * math.cos(math.radians(lat)))) * math.sin(bearing)
        prefixes.add(_geohash_encode(lat + dlat, lon + dlon, precision))
    return prefixes


def _listen_for_strikes(tile_prefixes: set[str], listen_seconds: float) -> list[dict]:
    """Blocking: connects to the public Blitzortung MQTT bridge, subscribes to
    the given geohash tile prefixes, and collects whatever strikes arrive
    within listen_seconds. This is a real-time SAMPLE, not a historical query
    -- a strike that occurs just before or after the listen window is missed.
    Any strike reported is genuinely real; an empty result honestly means
    "none observed in this window", not "none exist"."""
    strikes: list[dict] = []

    def on_connect(client, userdata, flags, rc, properties=None):
        for prefix in tile_prefixes:
            client.subscribe(f"blitzortung/1.1/{prefix}/#", qos=0)

    def on_message(client, userdata, msg):
        try:
            strikes.append(json.loads(msg.payload))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BLITZORTUNG_MQTT_HOST, BLITZORTUNG_MQTT_PORT, 60)
    client.loop_start()
    try:
        time.sleep(listen_seconds)
    finally:
        client.loop_stop()
        client.disconnect()
    return strikes


async def _fetch_lightning_live(lat: float, lon: float) -> dict:
    prefixes = _tile_prefixes(lat, lon, LIGHTNING_RADIUS_KM, GEOHASH_PRECISION)
    strikes = await asyncio.to_thread(_listen_for_strikes, prefixes, LIGHTNING_LISTEN_SECONDS)
    lightning_alerts = [
        {"lat": s["lat"], "lon": s["lon"], "time_unix_ns": s.get("time")}
        for s in strikes
        if _haversine_km(lat, lon, s["lat"], s["lon"]) <= LIGHTNING_RADIUS_KM
    ]
    return {"lightning_alerts": lightning_alerts}


async def get_lightning_alerts(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback(
        "blitzortung-mqtt", lambda: _fetch_lightning_live(lat, lon), LIGHTNING_SNAPSHOT
    )
