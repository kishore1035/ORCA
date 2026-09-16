import httpx
import pytest
import respx
from app.connectors import stormglass
from app.schemas import ConnectorResult


def _hour(time="2026-09-16T00:00:00+00:00", **params):
    return {"time": time, **params}


def test_pick_source_value_prefers_sg():
    assert stormglass._pick_source_value({"sg": 1.0, "noaa": 2.0, "dwd": 3.0}) == 1.0


def test_pick_source_value_falls_back_to_any_source_when_sg_missing():
    assert stormglass._pick_source_value({"noaa": 2.0, "dwd": 3.0}) in (2.0, 3.0)


def test_pick_source_value_returns_none_for_empty_or_missing():
    assert stormglass._pick_source_value({}) is None
    assert stormglass._pick_source_value(None) is None


@respx.mock
async def test_get_stormglass_marine_data_live_success(monkeypatch):
    monkeypatch.setattr(stormglass, "get_settings", lambda: type("S", (), {"stormglass_api_key": "test-key"})())
    respx.get("https://api.stormglass.io/v2/weather/point").mock(
        return_value=httpx.Response(
            200,
            json={
                "hours": [
                    _hour(
                        waveHeight={"sg": 0.64, "noaa": 0.73},
                        swellHeight={"sg": 1.06, "noaa": 0.42},
                        currentSpeed={"sg": 0.01, "noaa": 0.09},
                        waterTemperature={"sg": 28.25, "noaa": 26.93},
                        wavePeriod={"sg": 4.49, "noaa": 13.96},
                    )
                ],
                "meta": {"dailyQuota": 10, "requestCount": 1},
            },
        )
    )

    res = await stormglass.get_stormglass_marine_data(9.9679, 76.2444)
    assert isinstance(res, ConnectorResult)
    assert res.is_cached is False
    assert res.data["wave_height_m"] == 0.64
    assert res.data["swell_height_m"] == 1.06
    assert res.data["surface_current_speed_ms"] == 0.01
    assert res.data["sst_celsius"] == 28.25
    assert res.data["wave_period_s"] == 4.49
    assert len(res.data["parameters"]) == 5
    param_dict = {p["parameter"]: p for p in res.data["parameters"]}
    assert param_dict["significant_wave_height"]["value"] == 0.64
    assert param_dict["significant_wave_height"]["source"] == "stormglass"


async def test_get_stormglass_marine_data_falls_back_without_key(monkeypatch):
    monkeypatch.setattr(stormglass, "get_settings", lambda: type("S", (), {"stormglass_api_key": ""})())

    res = await stormglass.get_stormglass_marine_data(9.9679, 76.2444)
    assert res.is_cached is True
    assert res.data_status == "CACHED"
    assert "wave_height_m" in res.data


@respx.mock
async def test_get_stormglass_marine_data_falls_back_on_quota_exhausted(monkeypatch):
    monkeypatch.setattr(stormglass, "get_settings", lambda: type("S", (), {"stormglass_api_key": "test-key"})())
    respx.get("https://api.stormglass.io/v2/weather/point").mock(
        return_value=httpx.Response(402, json={"errors": {"key": "Daily quota exceeded"}})
    )

    res = await stormglass.get_stormglass_marine_data(9.9679, 76.2444)
    assert res.is_cached is True
