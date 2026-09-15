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


# Reference Indian coastal coordinates (State / Sector, Coastline Lat, Coastline Lon)
INDIAN_COASTLINE_POINTS: list[dict[str, Any]] = [
    # Gujarat
    {"sector": "Gujarat", "name": "Kandla / Gulf of Kutch", "lat": 23.00, "lon": 70.22, "coast_side": "west"},
    {"sector": "Gujarat", "name": "Dwarka", "lat": 22.24, "lon": 68.96, "coast_side": "west"},
    {"sector": "Gujarat", "name": "Porbandar", "lat": 21.64, "lon": 69.60, "coast_side": "west"},
    {"sector": "Gujarat", "name": "Veraval", "lat": 20.90, "lon": 70.36, "coast_side": "west"},
    {"sector": "Gujarat", "name": "Surat / Hazira", "lat": 21.11, "lon": 72.65, "coast_side": "west"},
    # Maharashtra
    {"sector": "Maharashtra", "name": "Dahanu", "lat": 19.97, "lon": 72.73, "coast_side": "west"},
    {"sector": "Maharashtra", "name": "Mumbai / Versova", "lat": 19.13, "lon": 72.81, "coast_side": "west"},
    {"sector": "Maharashtra", "name": "Alibaug", "lat": 18.64, "lon": 72.87, "coast_side": "west"},
    {"sector": "Maharashtra", "name": "Ratnagiri", "lat": 16.99, "lon": 73.28, "coast_side": "west"},
    {"sector": "Maharashtra", "name": "Malvan / Sindhudurg", "lat": 16.06, "lon": 73.46, "coast_side": "west"},
    # Goa
    {"sector": "Goa", "name": "Panaji / Mormugao", "lat": 15.42, "lon": 73.80, "coast_side": "west"},
    # Karnataka
    {"sector": "Karnataka", "name": "Karwar", "lat": 14.81, "lon": 74.13, "coast_side": "west"},
    {"sector": "Karnataka", "name": "Kumta", "lat": 14.42, "lon": 74.41, "coast_side": "west"},
    {"sector": "Karnataka", "name": "Bhatkal", "lat": 13.97, "lon": 74.55, "coast_side": "west"},
    {"sector": "Karnataka", "name": "Kundapura / Malpe", "lat": 13.35, "lon": 74.70, "coast_side": "west"},
    {"sector": "Karnataka", "name": "Mangaluru", "lat": 12.9141, "lon": 74.8560, "coast_side": "west"},
    # Kerala
    {"sector": "Kerala", "name": "Kasaragod", "lat": 12.50, "lon": 74.98, "coast_side": "west"},
    {"sector": "Kerala", "name": "Kannur", "lat": 11.87, "lon": 75.37, "coast_side": "west"},
    {"sector": "Kerala", "name": "Kozhikode", "lat": 11.25, "lon": 75.77, "coast_side": "west"},
    {"sector": "Kerala", "name": "Munambam / Kochi", "lat": 10.18, "lon": 76.17, "coast_side": "west"},
    {"sector": "Kerala", "name": "Kochi Harbour", "lat": 9.93, "lon": 76.27, "coast_side": "west"},
    {"sector": "Kerala", "name": "Alappuzha", "lat": 9.49, "lon": 76.33, "coast_side": "west"},
    {"sector": "Kerala", "name": "Kollam / Neendakara", "lat": 8.89, "lon": 76.55, "coast_side": "west"},
    {"sector": "Kerala", "name": "Vizhinjam", "lat": 8.38, "lon": 76.99, "coast_side": "west"},
    # Tamil Nadu
    {"sector": "Tamil Nadu", "name": "Kanyakumari", "lat": 8.08, "lon": 77.55, "coast_side": "south"},
    {"sector": "Tamil Nadu", "name": "Tuticorin", "lat": 8.80, "lon": 78.16, "coast_side": "east"},
    {"sector": "Tamil Nadu", "name": "Rameswaram", "lat": 9.28, "lon": 79.31, "coast_side": "east"},
    {"sector": "Tamil Nadu", "name": "Nagapattinam", "lat": 10.76, "lon": 79.84, "coast_side": "east"},
    {"sector": "Tamil Nadu", "name": "Cuddalore / Puducherry", "lat": 11.75, "lon": 79.77, "coast_side": "east"},
    {"sector": "Tamil Nadu", "name": "Mahabalipuram", "lat": 12.62, "lon": 80.19, "coast_side": "east"},
    {"sector": "Tamil Nadu", "name": "Chennai / Kasimedu", "lat": 13.12, "lon": 80.30, "coast_side": "east"},
    # Andhra Pradesh
    {"sector": "Andhra Pradesh", "name": "Nellore / Krishnapatnam", "lat": 14.25, "lon": 80.13, "coast_side": "east"},
    {"sector": "Andhra Pradesh", "name": "Machilipatnam", "lat": 16.18, "lon": 81.14, "coast_side": "east"},
    {"sector": "Andhra Pradesh", "name": "Kakinada", "lat": 16.98, "lon": 82.25, "coast_side": "east"},
    {"sector": "Andhra Pradesh", "name": "Visakhapatnam", "lat": 17.68, "lon": 83.22, "coast_side": "east"},
    {"sector": "Andhra Pradesh", "name": "Kalingapatnam", "lat": 18.33, "lon": 84.12, "coast_side": "east"},
    # Odisha
    {"sector": "Odisha", "name": "Gopalpur", "lat": 19.26, "lon": 84.91, "coast_side": "east"},
    {"sector": "Odisha", "name": "Puri", "lat": 19.80, "lon": 85.83, "coast_side": "east"},
    {"sector": "Odisha", "name": "Paradip", "lat": 20.31, "lon": 86.61, "coast_side": "east"},
    {"sector": "Odisha", "name": "Chandipur / Balasore", "lat": 21.47, "lon": 87.02, "coast_side": "east"},
    # West Bengal
    {"sector": "West Bengal", "name": "Digha", "lat": 21.63, "lon": 87.51, "coast_side": "east"},
    {"sector": "West Bengal", "name": "Haldia / Sagar Island", "lat": 21.78, "lon": 88.08, "coast_side": "east"},
    {"sector": "West Bengal", "name": "Bakkhali / Sundarbans", "lat": 21.56, "lon": 88.25, "coast_side": "east"},
    # Lakshadweep
    {"sector": "Lakshadweep", "name": "Kavaratti", "lat": 10.57, "lon": 72.64, "coast_side": "island"},
    {"sector": "Lakshadweep", "name": "Agatti", "lat": 10.85, "lon": 72.18, "coast_side": "island"},
    {"sector": "Lakshadweep", "name": "Minicoy", "lat": 8.28, "lon": 73.05, "coast_side": "island"},
    # Andaman & Nicobar
    {"sector": "Andaman & Nicobar", "name": "Port Blair", "lat": 11.62, "lon": 92.73, "coast_side": "island"},
    {"sector": "Andaman & Nicobar", "name": "Havelock / Swaraj Dweep", "lat": 11.98, "lon": 92.98, "coast_side": "island"},
    {"sector": "Andaman & Nicobar", "name": "Car Nicobar", "lat": 9.17, "lon": 92.78, "coast_side": "island"},
    {"sector": "Andaman & Nicobar", "name": "Campbell Bay", "lat": 7.00, "lon": 93.93, "coast_side": "island"},
]


def compute_coastal_distance(lat: float, lon: float) -> dict[str, Any]:
    """Computes distance to Indian coastline, nearest coastal sector, and marine coverage."""
    # Find nearest coastal reference point
    nearest = min(
        INDIAN_COASTLINE_POINTS,
        key=lambda pt: _haversine_km(lat, lon, pt["lat"], pt["lon"]),
    )
    dist_km = _haversine_km(lat, lon, nearest["lat"], nearest["lon"])

    coast_side = nearest.get("coast_side", "west")
    is_offshore = False

    if coast_side == "west":
        is_offshore = lon <= (nearest["lon"] + 0.05)
    elif coast_side == "east":
        is_offshore = lon >= (nearest["lon"] - 0.05)
    elif coast_side == "south":
        is_offshore = lat <= (nearest["lat"] + 0.05)
    elif coast_side == "island":
        is_offshore = dist_km <= 200.0

    # Coverage envelope for Indian Maritime & Coastal waters
    in_lat_bounds = 5.0 <= lat <= 24.5
    in_lon_bounds = 67.0 <= lon <= 95.0

    # An inland point > 50km from shoreline is out of marine coverage
    is_inland = not is_offshore and dist_km > 5.0
    is_deep_inland = not is_offshore and dist_km > 50.0

    in_marine_coverage = in_lat_bounds and in_lon_bounds and not is_deep_inland

    coverage_message = None
    if not in_marine_coverage:
        coverage_message = (
            f"Selected location ({lat:.4f}°N, {lon:.4f}°E) is {round(dist_km, 1)} km inland from "
            f"the nearest coast ({nearest['name']}, {nearest['sector']}). "
            "INCOIS marine forecasts and ocean models are only available for coastal zones (up to 50 km inland) "
            "and Indian maritime waters."
        )
    elif is_inland:
        coverage_message = (
            f"Selected point is {round(dist_km, 1)} km inland from {nearest['name']}. "
            f"Marine conditions are evaluated for the nearest coastal sector ({nearest['sector']} Coastal Waters, "
            f"{nearest['lat']:.3f}°N, {nearest['lon']:.3f}°E)."
        )

    return {
        "distance_to_coast_km": round(dist_km, 2),
        "is_offshore": is_offshore,
        "nearest_coastal_name": nearest["name"],
        "nearest_coastal_sector": nearest["sector"],
        "nearest_coastal_point": (nearest["lat"], nearest["lon"]),
        "in_marine_coverage": in_marine_coverage,
        "coverage_message": coverage_message,
    }


async def _reverse_geocode_live(lat: float, lon: float) -> dict[str, Any]:
    async with httpx.AsyncClient(
        timeout=10.0, headers={"User-Agent": "orca-marine-platform/0.1"}
    ) as client:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "zoom": 14},
        )
        resp.raise_for_status()
        data = resp.json()
        address = data.get("address", {})
        display_name = data.get("display_name", f"{lat:.4f}°N, {lon:.4f}°E")
        district = address.get("state_district") or address.get("county") or address.get("city")
        state = address.get("state")
        return {
            "display_name": display_name,
            "district": district,
            "state": state,
            "country": address.get("country", "India"),
        }


async def reverse_geocode(lat: float, lon: float) -> dict[str, Any]:
    """Reverse geocodes coordinates with local coastal fallback."""
    try:
        return await _reverse_geocode_live(lat, lon)
    except Exception:
        coastal = compute_coastal_distance(lat, lon)
        return {
            "display_name": f"{coastal['nearest_coastal_name']} Coastal Sector",
            "district": coastal["nearest_coastal_name"],
            "state": coastal["nearest_coastal_sector"],
            "country": "India",
        }


async def get_nearby_boundary(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback(
        source="overpass-osm-protected-areas",
        live_fetch=lambda: _fetch_nearby_boundary_live(lat, lon),
        snapshot_path=BOUNDARY_SNAPSHOT,
    )

