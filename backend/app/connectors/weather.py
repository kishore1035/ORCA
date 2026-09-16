from pathlib import Path
import httpx
from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots" / "weather.json"


def _parse_tide_series(hourly: dict) -> list[tuple[str, float]]:
    """Open-Meteo Marine's `sea_level_height_msl` is model-derived (~8km grid,
    referenced to mean sea level, not chart datum LAT) -- a real tide-aware
    signal, but not an official INCOIS tide table. Absent from older
    snapshots/mocks, so this degrades to an empty series, not an error."""
    heights = hourly.get("sea_level_height_msl")
    times = hourly.get("time")
    if not heights or not times:
        return []
    return list(zip(times, heights))


def _next_tide_extrema(
    series: list[tuple[str, float]]
) -> tuple[tuple[str, float] | None, tuple[str, float] | None]:
    """First local high and first local low in the series after its start."""
    next_high, next_low = None, None
    for i in range(1, len(series) - 1):
        _, h_prev = series[i - 1]
        t, h = series[i]
        _, h_next = series[i + 1]
        if h > h_prev and h > h_next:
            if next_high is None:
                next_high = (t, h)
        elif h < h_prev and h < h_next:
            if next_low is None:
                next_low = (t, h)
        if next_high is not None and next_low is not None:
            break
    return next_high, next_low


async def _live_fetch(lat: float, lon: float) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        marine_resp = await client.get(
            "https://marine-api.open-meteo.com/v1/marine",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wave_height,swell_wave_height,sea_level_height_msl",
                "timezone": "auto",
                "forecast_days": 2,
            },
        )
        marine_resp.raise_for_status()
        marine = marine_resp.json()

        wind_resp = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wind_speed_10m,wind_direction_10m",
                "timezone": "auto",
            },
        )
        wind_resp.raise_for_status()
        wind = wind_resp.json()

    result = {
        "wave_height_m": marine["hourly"]["wave_height"][0],
        "swell_height_m": marine["hourly"]["swell_wave_height"][0],
        "wind_speed_kmh": wind["hourly"]["wind_speed_10m"][0],
        "wind_direction_deg": wind["hourly"]["wind_direction_10m"][0],
        "forecast_time": wind["hourly"]["time"][0],
    }

    tide_series = _parse_tide_series(marine["hourly"])
    if tide_series:
        result["tide_height_m"] = tide_series[0][1]
        next_high, next_low = _next_tide_extrema(tide_series)
        if next_high:
            result["next_high_tide"] = {"time": next_high[0], "height_m": next_high[1]}
        if next_low:
            result["next_low_tide"] = {"time": next_low[0], "height_m": next_low[1]}

    return result


async def get_weather(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback(
        source="open-meteo-marine",
        live_fetch=lambda: _live_fetch(lat, lon),
        snapshot_path=SNAPSHOT_PATH,
    )
