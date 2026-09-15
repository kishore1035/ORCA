"""Route Safety Agent.

Uses searoute (offline, free, MIT-licensed) to compute a real shipping-lane
route between two points when one exists in its maritime network -- this is
genuine land-avoidance/shipping-lane pathfinding, not a hand-rolled
approximation. searoute's network is built for open-water port-to-port
routes; it returns a degenerate single-point result for short/nearshore
hops (e.g. within the same backwater/harbor), so this falls back to the
original direct-line waypoint interpolation for those cases -- output
always discloses which method was used via `route_source`.

Either way, hazard checking reuses the existing weather_agent/risk_agent at
each waypoint -- no new hazard-assessment logic, same as alerting.py's
proactive checks.
"""
import math

import searoute as sr

from app.agents.risk_agent import run_risk_agent
from app.agents.weather_agent import run_weather_agent
from app.schemas import TraceEntry

WAYPOINT_COUNT = 5
MAX_SEA_ROUTE_WAYPOINTS = 8
DETOUR_OFFSET_KM = 20.0
KM_PER_DEGREE_LAT = 111.0


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dlon = math.radians(lon2 - lon1)
    lat1r, lat2r = math.radians(lat1), math.radians(lat2)
    x = math.sin(dlon) * math.cos(lat2r)
    y = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def _interpolate_waypoints(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float, count: int
) -> list[tuple[float, float]]:
    return [
        (
            start_lat + (end_lat - start_lat) * i / (count - 1),
            start_lon + (end_lon - start_lon) * i / (count - 1),
        )
        for i in range(count)
    ]


def _offset_perpendicular(lat: float, lon: float, bearing_deg: float, distance_km: float) -> tuple[float, float]:
    perp_bearing = math.radians(bearing_deg + 90)
    dlat = (distance_km / KM_PER_DEGREE_LAT) * math.cos(perp_bearing)
    dlon = (distance_km / (KM_PER_DEGREE_LAT * math.cos(math.radians(lat)))) * math.sin(perp_bearing)
    return lat + dlat, lon + dlon


def _sample_waypoints(coords: list[tuple[float, float]], max_count: int) -> list[tuple[float, float]]:
    """Evenly downsamples a coordinate list to at most max_count points,
    always keeping the first and last (start/end of the route)."""
    if len(coords) <= max_count:
        return coords
    indices = [round(i * (len(coords) - 1) / (max_count - 1)) for i in range(max_count)]
    return [coords[i] for i in indices]


def _searoute_raw(start_lon: float, start_lat: float, end_lon: float, end_lat: float) -> dict:
    return sr.searoute((start_lon, start_lat), (end_lon, end_lat))


def _compute_sea_route(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float
) -> list[tuple[float, float]] | None:
    try:
        result = _searoute_raw(start_lon, start_lat, end_lon, end_lat)
    except Exception:
        return None
    coords = result.get("geometry", {}).get("coordinates", [])
    length = result.get("properties", {}).get("length", 0)
    if len(coords) < 3 or not length:
        # searoute's maritime network has no resolution here (a short/
        # nearshore hop, e.g. within the same harbor or backwater) -- not
        # an error, just outside what shipping-lane data can answer.
        return None
    return [(lat, lon) for lon, lat in coords]


async def _check_waypoint(lat: float, lon: float) -> dict:
    weather, _ = await run_weather_agent(lat, lon)
    risk, _ = await run_risk_agent(lat, lon, weather)
    return {"lat": lat, "lon": lon, "verdict": risk["verdict"], "reasons": risk["reasons"]}


async def run_route_agent(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float
) -> tuple[dict, TraceEntry]:
    sea_route = _compute_sea_route(start_lat, start_lon, end_lat, end_lon)
    if sea_route:
        route_source = "shipping_lanes"
        waypoint_coords = _sample_waypoints(sea_route, MAX_SEA_ROUTE_WAYPOINTS)
    else:
        route_source = "direct_line_fallback"
        waypoint_coords = _interpolate_waypoints(start_lat, start_lon, end_lat, end_lon, WAYPOINT_COUNT)

    bearing = _bearing_deg(start_lat, start_lon, end_lat, end_lon)
    waypoints = []
    for lat, lon in waypoint_coords:
        result = await _check_waypoint(lat, lon)
        if result["verdict"] == "unsafe":
            detour_lat, detour_lon = _offset_perpendicular(lat, lon, bearing, DETOUR_OFFSET_KM)
            detour_result = await _check_waypoint(detour_lat, detour_lon)
            result["detour"] = detour_result if detour_result["verdict"] == "safe" else None
        waypoints.append(result)

    overall_verdict = "safe" if all(w["verdict"] == "safe" for w in waypoints) else "hazardous_segments"
    output = {"waypoints": waypoints, "overall_verdict": overall_verdict, "route_source": route_source}
    trace = TraceEntry(
        agent="route",
        inputs={"start": [start_lat, start_lon], "end": [end_lat, end_lon]},
        output=output,
        sources=["open-meteo-marine", "gdacs-cyclone-tracker", "cached-lightning-snapshot"]
        + (["searoute-maritime-network"] if sea_route else []),
    )
    return output, trace
