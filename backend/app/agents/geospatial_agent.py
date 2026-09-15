from app.connectors.geospatial import geocode, nearest_boundary_distance_km
from app.schemas import TraceEntry

PROXIMITY_WARNING_KM = 5.0


async def run_geospatial_agent(place_name: str) -> tuple[dict, TraceEntry]:
    geo_result = await geocode(place_name)
    lat, lon = geo_result.data["lat"], geo_result.data["lon"]
    boundary_info = nearest_boundary_distance_km(lat, lon)
    output = {
        "lat": lat,
        "lon": lon,
        "resolved_name": geo_result.data["display_name"],
        "nearest_boundary": boundary_info["nearest_boundary"],
        "boundary_distance_km": boundary_info["distance_km"],
        "within_warning_zone": boundary_info["distance_km"] <= PROXIMITY_WARNING_KM,
    }
    trace = TraceEntry(
        agent="geospatial",
        inputs={"place_name": place_name},
        output=output,
        sources=[geo_result.source, boundary_info["source"]],
        fetched_at=geo_result.fetched_at,
        is_cached=geo_result.is_cached,
    )
    return output, trace
