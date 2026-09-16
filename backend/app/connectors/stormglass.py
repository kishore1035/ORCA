# backend/app/connectors/stormglass.py
"""Stormglass.io connector.

Real marine weather (wave height, swell, wave period, surface current speed,
water temperature) -- blends several forecast models (Stormglass's own "sg"
model, NOAA, ECMWF, ICON, DWD, Meteo) per point.

**Free-tier quota is severely limited: verified live at 10 requests/day for
the whole app**, not per-user (see `meta.dailyQuota` in a real response).
This connector will realistically only serve live data for roughly the
first 10 chat queries each calendar day; after that, every call fails over
to the disclosed cached snapshot exactly like IMD/MOSDAC without a key --
this is the intended, honest degradation, not a bug to work around with
request throttling or caching beyond what `fetch_with_fallback` already
does.
"""
from pathlib import Path
from typing import Any
import httpx

from app.config import get_settings
from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult, MarineParameter

SNAPSHOT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "snapshots" / "stormglass.json"
)

STORMGLASS_BASE_URL = "https://api.stormglass.io/v2/weather/point"

# Preferred data-source model, verified against a real live response: every
# parameter tried carried an "sg" (Stormglass's own blended model) value.
PREFERRED_SOURCE = "sg"

# (output field, MarineParameter name, unit, Stormglass param name)
_PARAM_MAP = [
    ("wave_height_m", "significant_wave_height", "m", "waveHeight"),
    ("swell_height_m", "swell_height", "m", "swellHeight"),
    ("wave_period_s", "wave_period", "s", "wavePeriod"),
    ("surface_current_speed_ms", "surface_current_speed", "m/s", "currentSpeed"),
    ("sst_celsius", "sst", "°C", "waterTemperature"),
]


def _pick_source_value(source_values: dict[str, float] | None) -> float | None:
    """Stormglass nests each parameter's value by forecast-model source,
    e.g. {"sg": 0.64, "noaa": 0.73} -- not a plain number. Prefers the "sg"
    blended model; falls back to whichever source is present otherwise."""
    if not source_values:
        return None
    if PREFERRED_SOURCE in source_values:
        return source_values[PREFERRED_SOURCE]
    return next(iter(source_values.values()), None)


async def _live_fetch_stormglass(lat: float, lon: float) -> dict:
    settings = get_settings()
    api_key = getattr(settings, "stormglass_api_key", "")
    if not api_key:
        raise ValueError("No Stormglass API key configured; triggering verified fallback")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            STORMGLASS_BASE_URL,
            headers={"Authorization": api_key},
            params={
                "lat": lat,
                "lng": lon,
                "params": ",".join(sg_param for _, _, _, sg_param in _PARAM_MAP),
            },
        )
        resp.raise_for_status()
        body = resp.json()

    hours = body.get("hours", [])
    if not hours:
        raise ValueError("Stormglass returned no forecast hours")
    current = hours[0]

    result: dict[str, Any] = {"forecast_time": current.get("time")}
    parameters: list[dict[str, Any]] = []
    for field_name, mp_name, unit, sg_param in _PARAM_MAP:
        value = _pick_source_value(current.get(sg_param))
        if value is None:
            continue
        result[field_name] = value
        parameters.append(
            MarineParameter(
                parameter=mp_name,
                value=value,
                unit=unit,
                latitude=lat,
                longitude=lon,
                timestamp=current.get("time", ""),
                source="stormglass",
                data_status="LIVE",
                confidence=0.9,
            ).model_dump()
        )
    result["parameters"] = parameters
    return result


async def get_stormglass_marine_data(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback(
        source="stormglass",
        live_fetch=lambda: _live_fetch_stormglass(lat, lon),
        snapshot_path=SNAPSHOT_PATH,
    )
