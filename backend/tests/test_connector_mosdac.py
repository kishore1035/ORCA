import pytest
from app.connectors.mosdac import get_mosdac_satellite_data
from app.schemas import ConnectorResult


@pytest.mark.asyncio
async def test_mosdac_non_blocking_fallback(monkeypatch):
    # Live fetch fails / credentials missing -> must gracefully return snapshot without blocking
    async def fail_live(lat, lon):
        raise ValueError("Auth unavailable")

    monkeypatch.setattr("app.connectors.mosdac._live_fetch_mosdac", fail_live)

    res = await get_mosdac_satellite_data(12.9141, 74.8560)
    assert isinstance(res, ConnectorResult)
    assert res.source == "ISRO-MOSDAC"
    assert res.is_cached is True
    assert res.data_status == "HISTORICAL"
    assert "chlorophyll_mg_m3" in res.data
    assert res.data["chlorophyll_mg_m3"] == 0.38
    assert "parameters" in res.data

    param_dict = {p["parameter"]: p for p in res.data["parameters"]}
    assert "chlorophyll" in param_dict
    assert param_dict["chlorophyll"]["value"] == 0.38
    assert param_dict["chlorophyll"]["unit"] == "mg/m³"


@pytest.mark.asyncio
async def test_mosdac_live_success(monkeypatch):
    async def fake_live(lat, lon):
        return {
            "chlorophyll_mg_m3": 0.42,
            "kd_490_per_meter": 0.10,
            "total_suspended_matter_g_m3": 3.8,
            "sst_celsius": 28.5,
        }

    monkeypatch.setattr("app.connectors.mosdac._live_fetch_mosdac", fake_live)

    res = await get_mosdac_satellite_data(12.9141, 74.8560)
    assert res.is_cached is False
    assert res.data_status == "LIVE"
    assert res.data["chlorophyll_mg_m3"] == 0.42
