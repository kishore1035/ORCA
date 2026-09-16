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
        fetched_at=datetime(2026, 9, 15, 0, 0, 0, tzinfo=timezone.utc), is_cached=False,
    )
    chl_result = ConnectorResult(
        data={"chlorophyll_mg_m3": 0.35}, source="noaa-erddap-chlorophyll",
        fetched_at=datetime(2026, 9, 15, 6, 0, 0, tzinfo=timezone.utc), is_cached=True,
    )
    trend_result = ConnectorResult(
        data={"sst_trend": [
            {"date": "2026-09-13T09:00:00Z", "sst_celsius": 27.5},
            {"date": "2026-09-14T09:00:00Z", "sst_celsius": 28.5},
        ]},
        source="noaa-erddap-sst-trend",
        fetched_at=datetime(2026, 9, 15, 3, 0, 0, tzinfo=timezone.utc), is_cached=False,
    )
    pfz_result = ConnectorResult(
        data={"sector": "SEC005", "nearest_landing_center": "Kunzhathur"},
        source="incois-pfz-advisory",
        fetched_at=datetime(2026, 9, 15, 1, 0, 0, tzinfo=timezone.utc), is_cached=False,
    )

    async def fake_get_sst(lat, lon):
        return sst_result

    async def fake_get_chlorophyll(lat, lon):
        return chl_result

    async def fake_get_sst_trend(lat, lon):
        return trend_result

    async def fake_get_pfz_advisory(lat, lon):
        return pfz_result

    monkeypatch.setattr(oaa, "get_sst", fake_get_sst)
    monkeypatch.setattr(oaa, "get_chlorophyll", fake_get_chlorophyll)
    monkeypatch.setattr(oaa, "get_sst_trend", fake_get_sst_trend)
    monkeypatch.setattr(oaa, "get_pfz_advisory", fake_get_pfz_advisory)

    output, trace = await oaa.run_ocean_analytics_agent(10.0, 76.0)

    assert output["pfz_likelihood"] == "high"
    assert output["sst_trend_celsius"] == trend_result.data["sst_trend"]
    assert output["sst_trend_direction"] == "warming"
    assert output["pfz_advisory"] == pfz_result.data
    assert trace.agent == "ocean_analytics"
    assert set(trace.sources) == {
        "noaa-erddap-sst", "noaa-erddap-chlorophyll", "noaa-erddap-sst-trend", "incois-pfz-advisory",
    }
    # Verify max() is used for fetched_at: should be the LATEST timestamp
    assert trace.fetched_at == datetime(2026, 9, 15, 6, 0, 0, tzinfo=timezone.utc)
    # Verify or is used for is_cached: any cached connector makes the whole result cached
    assert trace.is_cached is True


def test_trend_direction_stable_within_small_delta():
    direction = oaa._trend_direction([
        {"date": "d1", "sst_celsius": 28.0},
        {"date": "d2", "sst_celsius": 28.1},
    ])
    assert direction == "stable"


def test_trend_direction_empty_list_is_unknown():
    assert oaa._trend_direction([]) == "unknown"


def test_productivity_trend_declining_when_sst_moves_out_of_favorable_range():
    trend = [{"date": "d1", "sst_celsius": 28.0}, {"date": "d2", "sst_celsius": 25.0}]
    direction, note = oaa._productivity_trend(trend)
    assert direction == "declining"
    assert "28.0" in note and "25.0" in note


def test_productivity_trend_improving_when_sst_moves_into_favorable_range():
    trend = [{"date": "d1", "sst_celsius": 25.0}, {"date": "d2", "sst_celsius": 28.0}]
    direction, note = oaa._productivity_trend(trend)
    assert direction == "improving"


def test_productivity_trend_stable_when_favorability_unchanged():
    trend = [{"date": "d1", "sst_celsius": 28.0}, {"date": "d2", "sst_celsius": 28.5}]
    direction, note = oaa._productivity_trend(trend)
    assert direction == "stable"


def test_productivity_trend_unknown_for_empty_trend():
    direction, note = oaa._productivity_trend([])
    assert direction == "unknown"


def test_trend_direction_unknown_when_all_points_are_masked_null():
    # A real ERDDAP condition, not a fabrication: a near-shore point the 1km
    # MUR SST grid treats as land returns a JSON null for every day.
    trend = [{"date": "d1", "sst_celsius": None}, {"date": "d2", "sst_celsius": None}]
    assert oaa._trend_direction(trend) == "unknown"


def test_trend_direction_ignores_masked_points_when_enough_real_points_remain():
    trend = [
        {"date": "d1", "sst_celsius": None},
        {"date": "d2", "sst_celsius": 26.0},
        {"date": "d3", "sst_celsius": 28.0},
    ]
    assert oaa._trend_direction(trend) == "warming"


def test_productivity_trend_unknown_when_all_points_are_masked_null():
    trend = [{"date": "d1", "sst_celsius": None}, {"date": "d2", "sst_celsius": None}]
    direction, note = oaa._productivity_trend(trend)
    assert direction == "unknown"
    assert "No SST trend data" in note


def test_productivity_trend_ignores_masked_points_when_enough_real_points_remain():
    trend = [
        {"date": "d1", "sst_celsius": None},
        {"date": "d2", "sst_celsius": 25.0},
        {"date": "d3", "sst_celsius": 28.0},
    ]
    direction, note = oaa._productivity_trend(trend)
    assert direction == "improving"
