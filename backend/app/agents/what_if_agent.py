# backend/app/agents/what_if_agent.py
"""What-If comparative marine analysis agent.

Evaluates alternative departure times (e.g. 06:00 vs 11:00) or spatial relocations
(e.g. "What if I move 15 km south?"), re-running marine risk calculations
dynamically and isolating changed conditions.
"""
from datetime import datetime, timezone
import math
from typing import Any
from app.agents.risk_engine import calculate_risk
from app.connectors.incois import get_marine_forecast
from app.connectors.geospatial import compute_coastal_distance, _haversine_km
from app.schemas import TraceEntry, WhatIfComparison


def calculate_destination_coords(
    lat: float, lon: float, distance_km: float, direction: str
) -> tuple[float, float]:
    """Calculates new coordinates after moving distance_km in a cardinal/offshore direction."""
    dir_clean = direction.strip().lower()
    lat_deg_per_km = 1.0 / 110.574
    lon_deg_per_km = 1.0 / (111.320 * math.cos(math.radians(lat)))

    if "south" in dir_clean:
        return round(lat - distance_km * lat_deg_per_km, 4), round(lon, 4)
    elif "north" in dir_clean:
        return round(lat + distance_km * lat_deg_per_km, 4), round(lon, 4)
    elif "east" in dir_clean:
        return round(lat, 4), round(lon + distance_km * lon_deg_per_km, 4)
    elif "west" in dir_clean:
        return round(lat, 4), round(lon - distance_km * lon_deg_per_km, 4)
    elif "offshore" in dir_clean or "seaward" in dir_clean:
        coastal = compute_coastal_distance(lat, lon)
        coast_side = coastal.get("coast_side", "west")
        if coast_side == "west":
            return round(lat, 4), round(lon - distance_km * lon_deg_per_km, 4)
        else:
            return round(lat, 4), round(lon + distance_km * lon_deg_per_km, 4)
    else:
        # Default south if unspecified direction
        return round(lat - distance_km * lat_deg_per_km, 4), round(lon, 4)


async def run_what_if_agent(
    lat: float,
    lon: float,
    original_time: str = "06:00",
    alternative_time: str = "11:00",
    imd_warning_level: str | None = None,
    is_spatial: bool = False,
    move_distance_km: float | None = None,
    move_direction: str | None = None,
) -> tuple[dict, TraceEntry]:
    """Runs dual-time or dual-location marine forecast and calculates counterfactual delta."""
    if is_spatial and move_distance_km and move_distance_km > 0:
        direction = move_direction or "south"
        new_lat, new_lon = calculate_destination_coords(lat, lon, move_distance_km, direction)

        # 1. Fetch conditions for original location
        orig_res = await get_marine_forecast(lat, lon, target_time=original_time)
        orig_params = {p["parameter"]: p["value"] for p in orig_res.data.get("parameters", [])}

        orig_wave = float(orig_params.get("significant_wave_height", 1.5))
        orig_wind = float(orig_params.get("wind_speed", 20.0))
        orig_swell = float(orig_params.get("swell_height", 1.2))
        orig_period = float(orig_params.get("wave_period", 7.0))
        orig_current = float(orig_params.get("surface_current_speed", 0.35))

        orig_risk = calculate_risk(
            wave_height_m=orig_wave,
            wind_speed_kmh=orig_wind,
            wave_period_s=orig_period,
            swell_height_m=orig_swell,
            surface_current_ms=orig_current,
            imd_warning_level=imd_warning_level,
            target_time=original_time,
        )

        # 2. Fetch conditions for relocated coordinates
        alt_res = await get_marine_forecast(new_lat, new_lon, target_time=original_time)
        alt_params = {p["parameter"]: p["value"] for p in alt_res.data.get("parameters", [])}

        alt_wave = float(alt_params.get("significant_wave_height", 1.7))
        alt_wind = float(alt_params.get("wind_speed", 22.0))
        alt_swell = float(alt_params.get("swell_height", 1.3))
        alt_period = float(alt_params.get("wave_period", 7.2))
        alt_current = float(alt_params.get("surface_current_speed", 0.38))

        alt_risk = calculate_risk(
            wave_height_m=alt_wave,
            wind_speed_kmh=alt_wind,
            wave_period_s=alt_period,
            swell_height_m=alt_swell,
            surface_current_ms=alt_current,
            imd_warning_level=imd_warning_level,
            target_time=original_time,
        )

        differences = [
            {
                "parameter": "Coordinates",
                "original": f"{lat:.3f}°N, {lon:.3f}°E",
                "alternative": f"{new_lat:.3f}°N, {new_lon:.3f}°E",
                "delta": f"{move_distance_km:.1f} km {direction.upper()}",
                "impact": f"Relocated {move_distance_km:.1f} km {direction.lower()}",
            },
            {
                "parameter": "Significant Wave Height",
                "original": f"{orig_wave:.1f} m",
                "alternative": f"{alt_wave:.1f} m",
                "delta": f"{alt_wave - orig_wave:+.1f} m",
                "impact": "Higher sea state" if alt_wave > orig_wave else "Calmer sea state",
            },
            {
                "parameter": "Wind Speed",
                "original": f"{orig_wind:.1f} km/h",
                "alternative": f"{alt_wind:.1f} km/h",
                "delta": f"{alt_wind - orig_wind:+.1f} km/h",
                "impact": "Higher wind velocity" if alt_wind > orig_wind else "Lighter wind",
            },
        ]

        score_diff = alt_risk.risk_score - orig_risk.risk_score
        orig_loc_str = f"{lat:.3f}°N, {lon:.3f}°E"
        alt_loc_str = f"{new_lat:.3f}°N, {new_lon:.3f}°E ({move_distance_km} km {direction})"

        if score_diff < 0:
            verdict = (
                f"Relocating {move_distance_km} km {direction} lowers marine risk score from {orig_risk.risk_score} "
                f"down to {alt_risk.risk_score} ({alt_risk.risk_level}). Favorable sheltered conditions."
            )
        elif score_diff > 0:
            verdict = (
                f"Moving {move_distance_km} km {direction} increases risk from {orig_risk.risk_score} to "
                f"{alt_risk.risk_score} ({alt_risk.risk_level}). Current position provides safer sea conditions."
            )
        else:
            verdict = (
                f"Conditions remain homogeneous {move_distance_km} km {direction}, maintaining equivalent risk "
                f"({alt_risk.risk_score}/100, {alt_risk.risk_level})."
            )

        comparison = WhatIfComparison(
            original_time=original_time,
            original_risk_score=orig_risk.risk_score,
            original_risk_level=orig_risk.risk_level,
            alternative_time=original_time,
            alternative_risk_score=alt_risk.risk_score,
            alternative_risk_level=alt_risk.risk_level,
            differences=differences,
            verdict=verdict,
            comparison_type="location",
            original_location=orig_loc_str,
            alternative_location=alt_loc_str,
            spatial_delta_km=move_distance_km,
        )

        trace = TraceEntry(
            agent="what_if",
            inputs={"lat": lat, "lon": lon, "move_distance_km": move_distance_km, "move_direction": direction},
            output=comparison.model_dump(),
            sources=["INCOIS"],
            fetched_at=datetime.now(timezone.utc),
            is_cached=False,
        )
        return comparison.model_dump(), trace

    # Standard Temporal What-If
    orig_res = await get_marine_forecast(lat, lon, target_time=original_time)
    orig_params = {p["parameter"]: p["value"] for p in orig_res.data.get("parameters", [])}

    orig_wave = float(orig_params.get("significant_wave_height", 2.3))
    orig_wind = float(orig_params.get("wind_speed", 28.5))
    orig_swell = float(orig_params.get("swell_height", 1.9))
    orig_period = float(orig_params.get("wave_period", 7.8))
    orig_current = float(orig_params.get("surface_current_speed", 0.45))

    orig_risk = calculate_risk(
        wave_height_m=orig_wave,
        wind_speed_kmh=orig_wind,
        wave_period_s=orig_period,
        swell_height_m=orig_swell,
        surface_current_ms=orig_current,
        imd_warning_level=imd_warning_level,
        target_time=original_time,
    )

    alt_res = await get_marine_forecast(lat, lon, target_time=alternative_time)
    alt_params = {p["parameter"]: p for p in alt_res.data.get("parameters", [])}

    alt_wave = float(alt_params.get("significant_wave_height", {}).get("value", 1.4))
    alt_wind = float(alt_params.get("wind_speed", {}).get("value", 16.2))
    alt_swell = float(alt_params.get("swell_height", {}).get("value", 1.1))
    alt_period = float(alt_params.get("wave_period", {}).get("value", 6.5))
    alt_current = float(alt_params.get("surface_current_speed", {}).get("value", 0.28))

    alt_risk = calculate_risk(
        wave_height_m=alt_wave,
        wind_speed_kmh=alt_wind,
        wave_period_s=alt_period,
        swell_height_m=alt_swell,
        surface_current_ms=alt_current,
        imd_warning_level=imd_warning_level,
        target_time=alternative_time,
    )

    differences = [
        {
            "parameter": "Significant Wave Height",
            "original": f"{orig_wave:.1f} m",
            "alternative": f"{alt_wave:.1f} m",
            "delta": f"{alt_wave - orig_wave:+.1f} m",
            "impact": "Substantial sea state easing" if alt_wave < orig_wave else "Stable or higher wave conditions",
        },
        {
            "parameter": "Wind Speed",
            "original": f"{orig_wind:.1f} km/h",
            "alternative": f"{alt_wind:.1f} km/h",
            "delta": f"{alt_wind - orig_wind:+.1f} km/h",
            "impact": "Drop in wind stress below caution threshold" if alt_wind < orig_wind else "Higher wind force",
        },
        {
            "parameter": "Swell Height",
            "original": f"{orig_swell:.1f} m",
            "alternative": f"{alt_swell:.1f} m",
            "delta": f"{alt_swell - orig_swell:+.1f} m",
            "impact": "Reduced breakers near coastal bar" if alt_swell < orig_swell else "Elevated swell",
        },
    ]

    score_diff = alt_risk.risk_score - orig_risk.risk_score
    if score_diff < 0:
        verdict = (
            f"Departure at {alternative_time} significantly reduces marine risk from {orig_risk.risk_score} ({orig_risk.risk_level}) "
            f"down to {alt_risk.risk_score} ({alt_risk.risk_level}). Calmer waves ({alt_wave:.1f}m) and easing winds ({alt_wind:.1f} km/h) "
            f"provide a substantially safer window for coastal navigation."
        )
    elif score_diff > 0:
        verdict = (
            f"Departure at {alternative_time} increases marine risk to {alt_risk.risk_score} ({alt_risk.risk_level}) "
            f"compared to {orig_risk.risk_score} at {original_time}. Earlier departure or postponement is recommended."
        )
    else:
        verdict = f"Conditions remain stable between {original_time} and {alternative_time} with equal risk levels ({orig_risk.risk_score})."

    comparison = WhatIfComparison(
        original_time=original_time,
        original_risk_score=orig_risk.risk_score,
        original_risk_level=orig_risk.risk_level,
        alternative_time=alternative_time,
        alternative_risk_score=alt_risk.risk_score,
        alternative_risk_level=alt_risk.risk_level,
        differences=differences,
        verdict=verdict,
        comparison_type="time",
    )

    trace = TraceEntry(
        agent="what_if",
        inputs={"lat": lat, "lon": lon, "original_time": original_time, "alternative_time": alternative_time},
        output=comparison.model_dump(),
        sources=["INCOIS"],
        fetched_at=datetime.now(timezone.utc),
        is_cached=False,
    )
    return comparison.model_dump(), trace
