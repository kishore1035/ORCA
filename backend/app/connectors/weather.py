from pathlib import Path
import httpx
from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots" / "weather.json"


async def _live_fetch(lat: float, lon: float) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        marine_resp = await client.get(
            "https://marine-api.open-meteo.com/v1/marine",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wave_height,swell_wave_height",
                "timezone": "auto",
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

    return {
        "wave_height_m": marine["hourly"]["wave_height"][0],
        "swell_height_m": marine["hourly"]["swell_wave_height"][0],
        "wind_speed_kmh": wind["hourly"]["wind_speed_10m"][0],
        "wind_direction_deg": wind["hourly"]["wind_direction_10m"][0],
        "forecast_time": wind["hourly"]["time"][0],
    }


async def get_weather(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback(
        source="open-meteo-marine",
        live_fetch=lambda: _live_fetch(lat, lon),
        snapshot_path=SNAPSHOT_PATH,
    )
