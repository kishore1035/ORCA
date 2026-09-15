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
    alerts_result = ConnectorResult(
        data={"cyclone_alerts": [], "lightning_alerts": []},
        source="cached-alerts-snapshot",
        fetched_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        is_cached=True,
    )

    async def fake_get_alerts(lat, lon):
        return alerts_result

    monkeypatch.setattr(risk_agent, "get_alerts", fake_get_alerts)

    weather = {"wave_height_m": 1.0, "wind_speed_kmh": 15.0}
    output, trace = await risk_agent.run_risk_agent(10.0, 76.0, weather)

    assert output["verdict"] == "safe"
    assert trace.agent == "risk"
    assert trace.is_cached is True
