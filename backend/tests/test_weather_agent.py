from datetime import datetime, timezone
from app.agents import weather_agent
from app.schemas import ConnectorResult


async def test_run_weather_agent_returns_output_and_trace(monkeypatch):
    fixed_result = ConnectorResult(
        data={
            "wind_speed_kmh": 22.0,
            "wind_direction_deg": 190,
            "wave_height_m": 1.4,
            "swell_height_m": 0.9,
            "forecast_time": "2026-09-15T06:00",
        },
        source="open-meteo-marine",
        fetched_at=datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc),
        is_cached=False,
    )

    async def fake_get_weather(lat, lon):
        return fixed_result

    monkeypatch.setattr(weather_agent, "get_weather", fake_get_weather)

    output, trace = await weather_agent.run_weather_agent(10.0, 76.0)

    assert output["wind_speed_kmh"] == 22.0
    assert trace.agent == "weather"
    assert trace.sources == ["open-meteo-marine"]
    assert trace.is_cached is False
