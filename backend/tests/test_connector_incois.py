import pytest
from app.connectors.incois import get_incois_marine_forecast
from app.schemas import ConnectorResult, MarineParameter


@pytest.mark.asyncio
async def test_incois_fallback_snapshot(monkeypatch):
    # Simulate network failure to verify graceful fallback
    async def fail_live(lat, lon, target_time=None):
        raise TimeoutError("INCOIS connection timed out")

    monkeypatch.setattr("app.connectors.incois._live_fetch_incois", fail_live)

    res = await get_incois_marine_forecast(12.9141, 74.8560)
    assert isinstance(res, ConnectorResult)
    assert res.source == "INCOIS"
    assert res.is_cached is True
    assert res.data_status == "CACHED"
    assert "parameters" in res.data
    assert len(res.data["parameters"]) > 0

    # Verify wave height extracted
    param_dict = {p["parameter"]: p for p in res.data["parameters"]}
    assert "significant_wave_height" in param_dict
    assert param_dict["significant_wave_height"]["value"] == 2.3
    assert param_dict["significant_wave_height"]["unit"] == "m"


@pytest.mark.asyncio
async def test_incois_target_time_slot(monkeypatch):
    async def fail_live(lat, lon, target_time=None):
        raise ConnectionError("Offline")

    monkeypatch.setattr("app.connectors.incois._live_fetch_incois", fail_live)

    # Request 11:00 AM forecast slot
    res = await get_incois_marine_forecast(12.9141, 74.8560, target_time="11:00")
    param_dict = {p["parameter"]: p for p in res.data["parameters"]}
    assert param_dict["significant_wave_height"]["value"] == 1.4
    assert param_dict["wind_speed"]["value"] == 16.2


@pytest.mark.asyncio
async def test_incois_live_success(monkeypatch):
    async def fake_live(lat, lon, target_time=None):
        return {
            "current_conditions": {
                "significant_wave_height": 2.1,
                "wave_period": 7.5,
                "wind_speed_kmh": 25.0,
            }
        }

    monkeypatch.setattr("app.connectors.incois._live_fetch_incois", fake_live)

    res = await get_incois_marine_forecast(12.9141, 74.8560)
    assert res.is_cached is False
    assert res.data_status == "FORECAST"
    param_dict = {p["parameter"]: p for p in res.data["parameters"]}
    assert param_dict["significant_wave_height"]["value"] == 2.1
