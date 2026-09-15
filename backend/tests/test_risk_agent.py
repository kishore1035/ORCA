from datetime import datetime, timezone
from app.agents import risk_agent
from app.schemas import ConnectorResult


def test_assess_safe_when_all_below_thresholds():
    weather = {"wave_height_m": 1.0, "wind_speed_kmh": 15.0}
    verdict, reasons = risk_agent._assess(weather, {"cyclone_alerts": [], "lightning_alerts": []})
    assert verdict == "safe"
    assert len(reasons) == 1


def test_assess_unsafe_on_high_waves():
    weather = {"wave_height_m": 3.0, "wind_speed_kmh": 15.0}
    verdict, reasons = risk_agent._assess(weather, {"cyclone_alerts": [], "lightning_alerts": []})
    assert verdict == "unsafe"
    assert any("Wave height" in r for r in reasons)


def test_assess_unsafe_on_cyclone_alert():
    weather = {"wave_height_m": 1.0, "wind_speed_kmh": 15.0}
    alerts_data = {"cyclone_alerts": [{"name": "Cyclone Test"}], "lightning_alerts": []}
    verdict, reasons = risk_agent._assess(weather, alerts_data)
    assert verdict == "unsafe"
    assert any("Cyclone Test" in r for r in reasons)


async def test_run_risk_agent_returns_output_and_trace(monkeypatch):
    cyclone_result = ConnectorResult(
        data={"cyclone_alerts": []},
        source="gdacs-cyclone-tracker",
        fetched_at=datetime(2026, 9, 15, 6, 0, 0, tzinfo=timezone.utc),
        is_cached=False,
    )
    lightning_result = ConnectorResult(
        data={"lightning_alerts": []},
        source="cached-lightning-snapshot",
        fetched_at=datetime(2026, 9, 15, 0, 0, 0, tzinfo=timezone.utc),
        is_cached=True,
    )

    async def fake_get_cyclone_alerts(lat, lon):
        return cyclone_result

    async def fake_get_lightning_alerts(lat, lon):
        return lightning_result

    monkeypatch.setattr(risk_agent, "get_cyclone_alerts", fake_get_cyclone_alerts)
    monkeypatch.setattr(risk_agent, "get_lightning_alerts", fake_get_lightning_alerts)

    weather = {"wave_height_m": 1.0, "wind_speed_kmh": 15.0}
    output, trace = await risk_agent.run_risk_agent(10.0, 76.0, weather)

    assert output["verdict"] == "safe"
    assert trace.agent == "risk"
    assert set(trace.sources) == {"gdacs-cyclone-tracker", "cached-lightning-snapshot"}
    # or() semantics: cyclone is live but lightning is cached -> whole result is cached
    assert trace.is_cached is True
    # max() semantics: latest of the two fetched_at timestamps
    assert trace.fetched_at == datetime(2026, 9, 15, 6, 0, 0, tzinfo=timezone.utc)
