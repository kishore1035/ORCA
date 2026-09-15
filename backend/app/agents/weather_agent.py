from app.connectors.weather import get_weather
from app.schemas import TraceEntry


async def run_weather_agent(lat: float, lon: float) -> tuple[dict, TraceEntry]:
    result = await get_weather(lat, lon)
    output = {
        "wind_speed_kmh": result.data["wind_speed_kmh"],
        "wind_direction_deg": result.data["wind_direction_deg"],
        "wave_height_m": result.data["wave_height_m"],
        "swell_height_m": result.data["swell_height_m"],
        "forecast_time": result.data["forecast_time"],
    }
    trace = TraceEntry(
        agent="weather",
        inputs={"lat": lat, "lon": lon},
        output=output,
        sources=[result.source],
        fetched_at=result.fetched_at,
        is_cached=result.is_cached,
    )
    return output, trace
