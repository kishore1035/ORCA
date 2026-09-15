# backend/app/agents/geospatial_agent.py
"""Geospatial Agent.

Resolves place names or coordinates to canonical location, computes distance to coastline,
and checks proximity to marine protected areas and geofences.
"""
from app.connectors.geospatial import geocode, get_nearby_boundary, compute_coastal_distance, reverse_geocode
from app.schemas import TraceEntry

PROXIMITY_WARNING_KM = 5.0


async def run_geospatial_agent(
    place_name: str | None = None,
    coords: tuple[float, float] | None = None,
    location_metadata: dict | None = None,
) -> tuple[dict, TraceEntry]:
    is_cached = False
    sources = []
    fetched_at = None

    if coords is not None:
        lat, lon = coords
        resolved_name = (
            location_metadata.get("display_name")
            if location_metadata and location_metadata.get("display_name")
            else None
        )
        if not resolved_name:
            rev = await reverse_geocode(lat, lon)
            resolved_name = rev.get("display_name", f"{lat:.4f}°N, {lon:.4f}°E")
        sources.append(location_metadata.get("source", "COORDINATES") if location_metadata else "COORDINATES")
    else:
        # Legacy / place_name resolution
        geo_result = await geocode(place_name or "Mangaluru")
        lat, lon = geo_result.data["lat"], geo_result.data["lon"]
        resolved_name = geo_result.data["display_name"]
        sources.append(geo_result.source)
        fetched_at = geo_result.fetched_at
        is_cached = geo_result.is_cached

    # Compute coastal distance, offshore classification & marine coverage
    coastal = compute_coastal_distance(lat, lon)

    # Check nearby marine protected area / sanctuary
    boundary_result = await get_nearby_boundary(lat, lon)
    distance_km = boundary_result.data.get("distance_km")
    within_warning_zone = distance_km is not None and distance_km <= PROXIMITY_WARNING_KM

    sources.append(boundary_result.source)
    if boundary_result.fetched_at and (fetched_at is None or boundary_result.fetched_at > fetched_at):
        fetched_at = boundary_result.fetched_at
    is_cached = is_cached or boundary_result.is_cached

    output = {
        "lat": lat,
        "lon": lon,
        "resolved_name": resolved_name,
        "nearest_boundary": boundary_result.data.get("nearest_boundary"),
        "boundary_distance_km": distance_km,
        "within_warning_zone": within_warning_zone,
        "distance_to_coast_km": coastal["distance_to_coast_km"],
        "is_offshore": coastal["is_offshore"],
        "nearest_coastal_name": coastal["nearest_coastal_name"],
        "nearest_coastal_sector": coastal["nearest_coastal_sector"],
        "nearest_coastal_point": coastal["nearest_coastal_point"],
        "in_marine_coverage": coastal["in_marine_coverage"],
        "coverage_message": coastal["coverage_message"],
    }

    if within_warning_zone:
        output["geofence_warning"] = (
            f"Within {distance_km}km of {boundary_result.data['nearest_boundary']} "
            "-- check local marine protected area / boundary regulations before entering."
        )

    if coords is None and is_cached:
        output["location_fallback"] = True

    if not coastal["in_marine_coverage"] and coastal["coverage_message"]:
        output["coverage_warning"] = coastal["coverage_message"]

    trace = TraceEntry(
        agent="geospatial",
        inputs={"place_name": place_name, "coords": [lat, lon]},
        output=output,
        sources=sources,
        fetched_at=fetched_at,
        is_cached=is_cached,
    )
    return output, trace
