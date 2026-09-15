from datetime import datetime, timezone
from app.agents import ocean_analytics_agent as oaa
from app.schemas import ConnectorResult


def test_score_high_when_both_thresholds_met():
    likelihood, reasons = oaa._score(sst_c=28.5, chlorophyll=0.35)
    assert likelihood == "high"
    assert len(reasons) == 2


def test_score_low_when_neither_threshold_met():
    likelihood, _ = oaa._score(sst_c=22.0, chlorophyll=0.05)
    assert likelihood == "low"


def test_score_moderate_when_one_threshold_met():
    likelihood, _ = oaa._score(sst_c=28.0, chlorophyll=0.05)
    assert likelihood == "moderate"


async def test_run_ocean_analytics_agent_combines_both_connectors(monkeypatch):
    sst_result = ConnectorResult(
        data={"sst_celsius": 28.5}, source="noaa-erddap-sst",
        fetched_at=datetime(2026, 9, 15, tzinfo=timezone.utc), is_cached=False,
    )
    chl_result = ConnectorResult(
        data={"chlorophyll_mg_m3": 0.35}, source="noaa-erddap-chlorophyll",
        fetched_at=datetime(2026, 9, 15, tzinfo=timezone.utc), is_cached=False,
    )

    async def fake_get_sst(lat, lon):
        return sst_result

    async def fake_get_chlorophyll(lat, lon):
        return chl_result

    monkeypatch.setattr(oaa, "get_sst", fake_get_sst)
    monkeypatch.setattr(oaa, "get_chlorophyll", fake_get_chlorophyll)

    output, trace = await oaa.run_ocean_analytics_agent(10.0, 76.0)

    assert output["pfz_likelihood"] == "high"
    assert trace.agent == "ocean_analytics"
    assert set(trace.sources) == {"noaa-erddap-sst", "noaa-erddap-chlorophyll"}
