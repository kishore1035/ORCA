import json
import math
from pathlib import Path
import httpx
from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots"
GEOCODE_SNAPSHOT = DATA_DIR / "geocode.json"
BOUNDARY_SNAPSHOT = DATA_DIR / "nearby_boundary.json"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Marine-relevant protected-area search radius. Wide enough to surface a real
# nearby MPA/sanctuary for most coastal queries without pulling in the whole country.
BOUNDARY_SEARCH_RADIUS_M = 100_000
EARTH_RADIUS_KM = 6371.0


async def _geocode_live(place_name: str) -> dict:
    async with httpx.AsyncClient(
        timeout=10.0, headers={"User-Agent": "orca-marine-platform/0.1"}
    ) as client:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": place_name, "format": "json", "limit": 1},
        )
        resp.raise_for_status()
        results = resp.json()
    if not results:
        raise ValueError(f"No geocode result for {place_name!r}")
    return {
        "lat": float(results[0]["lat"]),
        "lon": float(results[0]["lon"]),
        "display_name": results[0]["display_name"],
    }


async def geocode(place_name: str) -> ConnectorResult:
    return await fetch_with_fallback(
        source="nominatim",
        live_fetch=lambda: _geocode_live(place_name),
        snapshot_path=GEOCODE_SNAPSHOT,
    )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


async def _fetch_nearby_boundary_live(lat: float, lon: float) -> dict:
    query = (
        f"[out:json][timeout:20];"
        f'(way["boundary"="protected_area"](around:{BOUNDARY_SEARCH_RADIUS_M},{lat},{lon});'
        f'relation["boundary"="protected_area"](around:{BOUNDARY_SEARCH_RADIUS_M},{lat},{lon}););'
        f"out center tags;"
    )
    async with httpx.AsyncClient(
        timeout=25.0, headers={"User-Agent": "orca-marine-platform/0.1"}
    ) as client:
        resp = await client.post(OVERPASS_URL, data={"data": query})
        resp.raise_for_status()
        payload = resp.json()

    candidates = []
    for element in payload.get("elements", []):
        name = element.get("tags", {}).get("name")
        center = element.get("center")
        if not name or not center:
            continue
        distance_km = _haversine_km(lat, lon, center["lat"], center["lon"])
        candidates.append((distance_km, name))

    if not candidates:
        return {"nearest_boundary": None, "distance_km": None}

    distance_km, name = min(candidates, key=lambda c: c[0])
    return {"nearest_boundary": name, "distance_km": round(distance_km, 1)}


async def get_nearby_boundary(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback(
        source="overpass-osm-protected-areas",
        live_fetch=lambda: _fetch_nearby_boundary_live(lat, lon),
        snapshot_path=BOUNDARY_SNAPSHOT,
    )
