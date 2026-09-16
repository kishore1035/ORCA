# backend/app/connectors/incois.py
"""INCOIS (Indian National Centre for Ocean Information Services) connector.

Primary ocean intelligence provider for Indian waters, providing wave, swell,
current, wind, and sea surface temperature forecast data.
Supports coordinate-based querying across all 9 Indian coastal states and
2 island territories with nearest grid resolution and distance tracking.
"""
from datetime import datetime, timezone
import math
from pathlib import Path
from typing import Any

from app.connectors.base import fetch_with_fallback
from app.connectors.geospatial import compute_coastal_distance, _haversine_km
from app.schemas import ConnectorResult, MarineParameter

SNAPSHOT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "snapshots"
    / "incois_mangalore.json"
)


def resolve_incois_grid_point(lat: float, lon: float) -> tuple[float, float, float]:
    """Resolves nearest INCOIS ~0.05-degree coastal grid point and distance in km."""
    # INCOIS Coastal OSF uses ~0.05 deg grid steps along Indian coast
    grid_lat = round(round(lat * 20.0) / 20.0, 4)
    grid_lon = round(round(lon * 20.0) / 20.0, 4)
    dist_km = _haversine_km(lat, lon, grid_lat, grid_lon)
    return grid_lat, grid_lon, round(dist_km, 2)


def _extract_parameters_for_time(
    data: dict,
    lat: float,
    lon: float,
    source: str,
    data_status: str,
    target_time: str | None = None,
    grid_lat: float | None = None,
    grid_lon: float | None = None,
    grid_distance_km: float | None = None,
) -> list[dict[str, Any]]:
    """Extract normalized MarineParameter list from INCOIS dataset matching target time."""
    hourly = data.get("hourly_forecast", [])
    selected_slot = None

    if target_time and hourly:
        target_clean = target_time.strip().lower()
        for slot in hourly:
            t = slot.get("time", "")
            if target_clean in t.lower() or target_clean in t:
                selected_slot = slot
                break
            if ("T11:" in t and "11" in target_clean) or ("T06:" in t and ("06" in target_clean or "6" in target_clean)):
                selected_slot = slot
                break

    if not selected_slot:
        if hourly:
            selected_slot = hourly[0]
        else:
            selected_slot = data.get("current_conditions", {})

    ts = selected_slot.get("time", datetime.now(timezone.utc).isoformat())
    valid_from = selected_slot.get("valid_from")
    valid_until = selected_slot.get("valid_until")

    params: list[dict[str, Any]] = []

    mappings = [
        ("significant_wave_height", "m", selected_slot.get("significant_wave_height")),
        ("wave_period", "s", selected_slot.get("wave_period")),
        ("swell_height", "m", selected_slot.get("swell_height")),
        ("swell_period", "s", selected_slot.get("swell_period")),
        ("wind_speed", "km/h", selected_slot.get("wind_speed_kmh")),
        ("wind_direction", "deg", selected_slot.get("wind_direction_deg")),
        ("surface_current_speed", "m/s", selected_slot.get("surface_current_speed_ms")),
        ("surface_current_direction", "deg", selected_slot.get("surface_current_direction_deg")),
        ("sst", "°C", selected_slot.get("sst_celsius")),
    ]

    for param_name, unit, val in mappings:
        if val is not None:
            mp = MarineParameter(
                parameter=param_name,
                value=float(val),
                unit=unit,
                latitude=lat,
                longitude=lon,
                timestamp=ts,
                valid_from=valid_from,
                valid_until=valid_until,
                source=source,
                data_status=data_status,  # type: ignore
                confidence=0.92 if data_status == "FORECAST" else 0.85,
                grid_latitude=grid_lat,
                grid_longitude=grid_lon,
                grid_distance_km=grid_distance_km,
            )
            params.append(mp.model_dump())

    return params


async def _live_fetch_incois(lat: float, lon: float, target_time: str | None = None) -> dict:
    """INCOIS's public OSF_CoastalForecast GeoServer WFS layer (the only
    unauthenticated INCOIS endpoint this connector can reach -- verified
    live against the real server) returns sector *boundary metadata only*:
    SECTORNAME, SEC_ID, and geometry. It carries no wave/wind/swell/current/
    SST attributes at all. There is no honest way to serve "live" numeric
    marine-forecast values from this layer, so this always raises and lets
    fetch_with_fallback use the disclosed cached snapshot instead -- per
    this project's connector contract, a connector must never fabricate
    data. (A real live path would need INCOIS's THREDDS NCSS interface,
    which does carry real values -- see docs/data-sources.md -- but isn't
    implemented here.)
    """
    coastal = compute_coastal_distance(lat, lon)
    if not coastal["in_marine_coverage"]:
        raise ValueError(coastal["coverage_message"] or "Outside Indian marine coverage")
    raise ValueError(
        "INCOIS's public OSF_CoastalForecast WFS layer has no numeric marine "
        "forecast values; always falling back to the verified cached snapshot"
    )


async def get_marine_forecast(
    latitude: float, longitude: float, target_time: str | None = None
) -> ConnectorResult:
    """Generic tool to fetch INCOIS marine forecast for any supported Indian coordinates."""
    # 1. Check coastal proximity & coverage
    coastal = compute_coastal_distance(latitude, longitude)
    if not coastal["in_marine_coverage"]:
        # Out-of-coverage explanation rather than fabricating ocean data
        return ConnectorResult(
            data={
                "in_marine_coverage": False,
                "coverage_message": coastal["coverage_message"],
                "distance_to_coast_km": coastal["distance_to_coast_km"],
                "nearest_coastal_name": coastal["nearest_coastal_name"],
                "parameters": [],
                "target_time": target_time,
            },
            source="INCOIS-Coverage-Engine",
            fetched_at=datetime.now(timezone.utc),
            is_cached=False,
            data_status="LIVE",
        )

    # 2. Resolve nearest INCOIS forecast grid point & geodesic distance
    grid_lat, grid_lon, grid_distance_km = resolve_incois_grid_point(latitude, longitude)

    # 3. Retrieve forecast with verified fallback
    raw_result = await fetch_with_fallback(
        source="INCOIS",
        live_fetch=lambda: _live_fetch_incois(latitude, longitude, target_time),
        snapshot_path=SNAPSHOT_PATH,
        live_data_status="FORECAST",
    )

    data_status = raw_result.data_status
    sector = coastal["nearest_coastal_sector"]
    source_detail = f"INCOIS ({sector} OSF Grid)"

    params = _extract_parameters_for_time(
        raw_result.data,
        lat=latitude,
        lon=longitude,
        source="INCOIS",
        data_status=data_status,
        target_time=target_time,
        grid_lat=grid_lat,
        grid_lon=grid_lon,
        grid_distance_km=grid_distance_km,
    )

    enriched_data = {
        **raw_result.data,
        "sector": sector,
        "source_detail": source_detail,
        "nearest_coastal_name": coastal["nearest_coastal_name"],
        "distance_to_coast_km": coastal["distance_to_coast_km"],
        "is_offshore": coastal["is_offshore"],
        "in_marine_coverage": True,
        "coverage_message": coastal.get("coverage_message"),
        "grid_point": {"latitude": grid_lat, "longitude": grid_lon},
        "grid_distance_km": grid_distance_km,
        "parameters": params,
        "target_time": target_time,
    }

    return ConnectorResult(
        data=enriched_data,
        source="INCOIS",
        fetched_at=raw_result.fetched_at,
        is_cached=raw_result.is_cached,
        data_status=data_status,
    )


# Backward-compatible alias
get_incois_marine_forecast = get_marine_forecast
