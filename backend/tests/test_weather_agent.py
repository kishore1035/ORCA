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


async def test_run_weather_agent_surfaces_tide_data(monkeypatch):
    fixed_result = ConnectorResult(
        data={
            "wind_speed_kmh": 22.0,
            "wind_direction_deg": 190,
            "wave_height_m": 1.4,
            "swell_height_m": 0.9,
            "forecast_time": "2026-09-15T06:00",
            "tide_height_m": 1.0,
            "next_high_tide": {"time": "2026-09-15T08:00", "height_m": 2.0},
            "next_low_tide": {"time": "2026-09-15T14:00", "height_m": 0.0},
        },
        source="open-meteo-marine",
        fetched_at=datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc),
        is_cached=False,
    )

    async def fake_get_weather_live(lat, lon):
        return fixed_result

    async def fake_no_enrichment(*args, **kwargs):
        return None

    monkeypatch.setattr(weather_agent, "get_weather", fake_get_weather_live)
    monkeypatch.setattr(weather_agent, "get_marine_forecast", fake_no_enrichment)
    monkeypatch.setattr(weather_agent, "get_imd_warnings", fake_no_enrichment)
    monkeypatch.setattr(weather_agent, "get_stormglass_marine_data", fake_no_enrichment)

    output, trace = await weather_agent.run_weather_agent(10.0, 76.0)

    assert output["tide_height_m"] == 1.0
    assert output["next_high_tide"] == {"time": "2026-09-15T08:00", "height_m": 2.0}
    assert output["next_low_tide"] == {"time": "2026-09-15T14:00", "height_m": 0.0}
    tide_params = [p for p in output["parameters"] if p["parameter"] == "tide_height"]
    assert len(tide_params) == 1
    assert tide_params[0]["value"] == 1.0
    assert tide_params[0]["source"] == "open-meteo-marine"
    assert tide_params[0]["unit"] == "m"


async def test_run_weather_agent_stormglass_enrichment_overrides_base_values(monkeypatch):
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
    stormglass_result = ConnectorResult(
        data={
            "wave_height_m": 0.64,
            "swell_height_m": 1.06,
            "wave_period_s": 4.49,
            "surface_current_speed_ms": 0.01,
            "sst_celsius": 28.25,
            "parameters": [
                {
                    "parameter": "significant_wave_height", "value": 0.64, "unit": "m",
                    "latitude": 10.0, "longitude": 76.0, "timestamp": "2026-09-15T06:00",
                    "source": "stormglass", "data_status": "LIVE", "confidence": 0.9,
                },
            ],
        },
        source="stormglass",
        fetched_at=datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc),
        is_cached=False,
    )

    async def fake_get_weather_live(lat, lon):
        return fixed_result

    async def fake_no_enrichment(*args, **kwargs):
        return None

    async def fake_stormglass(lat, lon):
        return stormglass_result

    monkeypatch.setattr(weather_agent, "get_weather", fake_get_weather_live)
    monkeypatch.setattr(weather_agent, "get_marine_forecast", fake_no_enrichment)
    monkeypatch.setattr(weather_agent, "get_imd_warnings", fake_no_enrichment)
    monkeypatch.setattr(weather_agent, "get_stormglass_marine_data", fake_stormglass)

    output, trace = await weather_agent.run_weather_agent(10.0, 76.0)

    assert output["wave_height_m"] == 0.64
    assert output["swell_height_m"] == 1.06
    assert output["wave_period_s"] == 4.49
    assert output["surface_current_speed_ms"] == 0.01
    assert "stormglass" in trace.sources
    sg_params = [p for p in output["parameters"] if p["source"] == "stormglass"]
    assert len(sg_params) == 1
