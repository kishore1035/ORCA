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


@respx.mock
async def test_get_weather_live_includes_tide_data():
    times = [f"2026-09-15T{h:02d}:00" for h in range(7)]
    respx.get("https://marine-api.open-meteo.com/v1/marine").mock(
        return_value=httpx.Response(
            200,
            json={
                "hourly": {
                    "wave_height": [1.5],
                    "swell_wave_height": [1.0],
                    "sea_level_height_msl": [1.0, 1.5, 2.0, 1.0, 0.0, 0.5, 1.2],
                    "time": times,
                }
            },
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
    assert result.data["tide_height_m"] == 1.0
    assert result.data["next_high_tide"] == {"time": times[2], "height_m": 2.0}
    assert result.data["next_low_tide"] == {"time": times[4], "height_m": 0.0}


def test_parse_tide_series_returns_empty_when_missing():
    assert weather._parse_tide_series({"wave_height": [1.0]}) == []


def test_next_tide_extrema_finds_first_high_and_low():
    series = [
        ("t0", 1.0), ("t1", 1.5), ("t2", 2.0),
        ("t3", 1.0), ("t4", 0.0), ("t5", 0.5), ("t6", 1.2),
    ]
    high, low = weather._next_tide_extrema(series)
    assert high == ("t2", 2.0)
    assert low == ("t4", 0.0)


def test_next_tide_extrema_handles_short_series():
    assert weather._next_tide_extrema([]) == (None, None)
    assert weather._next_tide_extrema([("t0", 1.0)]) == (None, None)
