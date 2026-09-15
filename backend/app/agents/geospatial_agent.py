from app.connectors.geospatial import geocode, get_nearby_boundary
from app.schemas import TraceEntry

PROXIMITY_WARNING_KM = 5.0


async def run_geospatial_agent(place_name: str) -> tuple[dict, TraceEntry]:
    geo_result = await geocode(place_name)
    lat, lon = geo_result.data["lat"], geo_result.data["lon"]
    boundary_result = await get_nearby_boundary(lat, lon)
    distance_km = boundary_result.data["distance_km"]
    within_warning_zone = distance_km is not None and distance_km <= PROXIMITY_WARNING_KM
    output = {
        "lat": lat,
        "lon": lon,
        "resolved_name": geo_result.data["display_name"],
        "nearest_boundary": boundary_result.data["nearest_boundary"],
        "boundary_distance_km": distance_km,
        "within_warning_zone": within_warning_zone,
    }
    if within_warning_zone:
        # Deterministic, code-guaranteed warning -- not left to the reporting LLM's
        # discretion to notice and mention on its own.
        output["geofence_warning"] = (
            f"Within {distance_km}km of {boundary_result.data['nearest_boundary']} "
            "-- check local marine protected area / boundary regulations before entering."
        )
    if geo_result.is_cached:
        # The live geocode failed and fell back to the committed snapshot, which
        # always resolves to the same fixed location regardless of place_name --
        # surface that so the trace/UI don't silently show the wrong place.
        output["location_fallback"] = True
    trace = TraceEntry(
        agent="geospatial",
        inputs={"place_name": place_name},
        output=output,
        sources=[geo_result.source, boundary_result.source],
        fetched_at=max(geo_result.fetched_at, boundary_result.fetched_at),
        is_cached=geo_result.is_cached or boundary_result.is_cached,
    )
    return output, trace
