import json
from pathlib import Path
import httpx
from shapely.geometry import Point, shape
from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots"
GEOCODE_SNAPSHOT = DATA_DIR / "geocode.json"
MPA_BOUNDARIES_PATH = DATA_DIR / "mpa_boundaries.geojson"

KM_PER_DEGREE = 111.0


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


def nearest_boundary_distance_km(lat: float, lon: float) -> dict:
    """Static MPA/international-boundary snapshot check (Phase 1 has no live feed)."""
    boundaries = json.loads(MPA_BOUNDARIES_PATH.read_text())
    point = Point(lon, lat)
    nearest_name = None
    nearest_distance_deg = float("inf")
    for feature in boundaries["features"]:
        geom = shape(feature["geometry"])
        distance_deg = point.distance(geom)
        if distance_deg < nearest_distance_deg:
            nearest_distance_deg = distance_deg
            nearest_name = feature["properties"]["name"]
    return {
        "nearest_boundary": nearest_name,
        "distance_km": round(nearest_distance_deg * KM_PER_DEGREE, 1),
        "source": "static-mpa-imbl-snapshot",
    }
