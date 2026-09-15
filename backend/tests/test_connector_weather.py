import httpx
import respx
from app.connectors import weather


@respx.mock
async def test_get_weather_live_success():
    respx.get("https://marine-api.open-meteo.com/v1/marine").mock(
        return_value=httpx.Response(
            200, json={"hourly": {"wave_height": [1.5], "swell_wave_height": [1.0]}}
        )
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(
            200,
            json={
                "hourly": {
                    "wind_speed_10m": [20.0],
                    "wind_direction_10m": [180],
                    "time": ["2026-09-15T06:00"],
                }
            },
        )
    )
    result = await weather.get_weather(10.0, 76.0)
    assert result.is_cached is False
    assert result.data["wave_height_m"] == 1.5
    assert result.data["wind_speed_kmh"] == 20.0


@respx.mock
async def test_get_weather_falls_back_on_failure():
    respx.get("https://marine-api.open-meteo.com/v1/marine").mock(
        side_effect=httpx.ConnectError("boom")
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        side_effect=httpx.ConnectError("boom")
    )
    result = await weather.get_weather(10.0, 76.0)
    assert result.is_cached is True
    assert result.data["wave_height_m"] == 1.2
