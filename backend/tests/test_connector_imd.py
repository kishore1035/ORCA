import pytest
from app.connectors.imd import get_imd_warnings
from app.schemas import ConnectorResult


@pytest.mark.asyncio
async def test_imd_fallback_snapshot(monkeypatch):
    # Simulate live fetch failure to verify fallback
    async def fail_live(lat, lon):
        raise ConnectionError("IMD gateway unreachable")

    monkeypatch.setattr("app.connectors.imd._live_fetch_imd", fail_live)

    res = await get_imd_warnings(12.9141, 74.8560)
    assert isinstance(res, ConnectorResult)
    assert res.source == "IMD"
    assert res.is_cached is True
    assert res.data_status == "CACHED"
    assert res.data["warning_level"] == "Yellow"
    assert "coastal_bulletin" in res.data
    assert "parameters" in res.data

    param_dict = {p["parameter"]: p for p in res.data["parameters"]}
    assert "weather_warning_level" in param_dict
    assert param_dict["weather_warning_level"]["value"] == "Yellow"
    assert "rainfall_forecast" in param_dict
    assert param_dict["rainfall_forecast"]["value"] == 18.5


@pytest.mark.asyncio
async def test_imd_live_success(monkeypatch):
    async def fake_live(lat, lon):
        return {
            "warning_level": "Red",
            "warning_type": "Cyclone Warning",
            "coastal_bulletin": "Gale winds warning",
            "port_warning_signal": 8,
            "rainfall_forecast_mm": 55.0,
            "cyclone_alerts": [{"name": "Cyclone Test"}],
            "valid_from": "2026-09-16T00:00:00Z",
            "valid_until": "2026-09-16T23:59:59Z",
        }

    monkeypatch.setattr("app.connectors.imd._live_fetch_imd", fake_live)

    res = await get_imd_warnings(12.9141, 74.8560)
    assert res.is_cached is False
    assert res.data_status == "FORECAST"
    assert res.data["warning_level"] == "Red"
    param_dict = {p["parameter"]: p for p in res.data["parameters"]}
    assert param_dict["port_warning_signal"]["value"] == 8
