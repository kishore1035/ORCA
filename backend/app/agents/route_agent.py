"""Route Safety Agent -- deliberately scoped, per an explicit design decision
confirmed with the user: this is a waypoint hazard SCAN, not a navigational
path planner. It answers "is this route safe, and where's it risky", not
"here is the GPS-optimal path". No land-avoidance, no shipping-lane data,
no bathymetry -- waypoints are simple linear interpolation between start and
end, which is a real simplification for anything but short coastal hops.

Reuses the existing weather_agent/risk_agent at each waypoint -- no new
hazard-assessment logic, same as alerting.py's proactive checks.
"""
import math

from app.agents.risk_agent import run_risk_agent
from app.agents.weather_agent import run_weather_agent
from app.schemas import TraceEntry

WAYPOINT_COUNT = 5
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


async def _check_waypoint(lat: float, lon: float) -> dict:
    weather, _ = await run_weather_agent(lat, lon)
    risk, _ = await run_risk_agent(lat, lon, weather)
    return {"lat": lat, "lon": lon, "verdict": risk["verdict"], "reasons": risk["reasons"]}


async def run_route_agent(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float
) -> tuple[dict, TraceEntry]:
    bearing = _bearing_deg(start_lat, start_lon, end_lat, end_lon)
    waypoints = []
    for lat, lon in _interpolate_waypoints(start_lat, start_lon, end_lat, end_lon, WAYPOINT_COUNT):
        result = await _check_waypoint(lat, lon)
        if result["verdict"] == "unsafe":
            detour_lat, detour_lon = _offset_perpendicular(lat, lon, bearing, DETOUR_OFFSET_KM)
            detour_result = await _check_waypoint(detour_lat, detour_lon)
            result["detour"] = detour_result if detour_result["verdict"] == "safe" else None
        waypoints.append(result)

    overall_verdict = "safe" if all(w["verdict"] == "safe" for w in waypoints) else "hazardous_segments"
    output = {"waypoints": waypoints, "overall_verdict": overall_verdict}
    trace = TraceEntry(
        agent="route",
        inputs={"start": [start_lat, start_lon], "end": [end_lat, end_lon]},
        output=output,
        sources=["open-meteo-marine", "gdacs-cyclone-tracker", "cached-lightning-snapshot"],
    )
    return output, trace
