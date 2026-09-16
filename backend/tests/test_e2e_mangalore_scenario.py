import pytest
from unittest.mock import AsyncMock
import respx
import httpx
from app.connectors import alerts
from app.graph import build_graph
from app import graph as graph_module


def _mock_connectors(monkeypatch):
    monkeypatch.setattr(alerts, "_listen_for_strikes", lambda prefixes, listen_seconds: [])
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(
            200, json=[{"lat": "12.9141", "lon": "74.8560", "display_name": "Mangaluru, Karnataka, India"}]
        )
    )
    respx.get("https://marine-api.open-meteo.com/v1/marine").mock(
        return_value=httpx.Response(200, json={"hourly": {"wave_height": [1.2], "swell_wave_height": [0.6]}})
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(
            200, json={"hourly": {"wind_speed_10m": [18.0], "wind_direction_10m": [220], "time": ["2026-09-16T06:00"]}}
        )
    )
    respx.get(url__regex=r"jplMURSST41\.json").mock(
        return_value=httpx.Response(200, json={"table": {"rows": [["t", 12.9141, 74.8560, 28.8]]}})
    )
    respx.get(url__regex=r"erdMH1chla1day\.json").mock(
        return_value=httpx.Response(200, json={"table": {"rows": [["t", 12.9141, 74.8560, 0.42]]}})
    )
    respx.get(url__regex=r"gdacs\.org/gdacsapi/api/events/geteventlist/SEARCH").mock(
        return_value=httpx.Response(200, json={"features": []})
    )


@pytest.mark.asyncio
@respx.mock
async def test_mangalore_fishing_query_e2e(monkeypatch):
    _mock_connectors(monkeypatch)
    monkeypatch.setattr(
        graph_module, "create_plan",
        AsyncMock(return_value={
            "intent": "fishing safety check",
            "place_name": "Mangaluru",
            "target_time": "06:00",
            "agents": ["weather", "risk", "ocean_analytics"],
            "response_language": "English",
        }),
    )
    monkeypatch.setattr(
        graph_module, "synthesize_answer",
        AsyncMock(return_value="RECOMMENDATION: PROCEED WITH CAUTION. Risk Score: 38/100 (MODERATE). Wave height is 1.3m from INCOIS."),
    )

    graph = build_graph(client=object())
    
    # Query 1: Can I go fishing near Mangaluru tomorrow at 6 AM?
    state = await graph.ainvoke({
        "message": "Can I go fishing near Mangaluru tomorrow at 6 AM?",
        "history": [],
    })

    assert state.get("final_answer") is not None
    assert "risk_result" in state
    risk = state["risk_result"]
    assert "risk_score" in risk
    assert 0 <= risk["risk_score"] <= 100
    assert risk["risk_level"] in ["LOW", "MODERATE", "HIGH", "EXTREME"]
    assert "recommendation" in risk
    assert len(risk["factors"]) > 0

    # Verification result
    assert "verification_result" in state
    verification = state["verification_result"]
    assert "INCOIS" in verification["sources"]
    assert "IMD" in verification["sources"]
    assert verification["data_status"] in ["FORECAST", "LIVE", "CACHED"]

    # Evidence parameters
    assert "evidence" in state
    evidence = state["evidence"]
    assert len(evidence) >= 5
    param_names = [p["parameter"] for p in evidence]
    assert "significant_wave_height" in param_names
    assert "wind_speed" in param_names
    assert "weather_warning_level" in param_names

    for param in evidence:
        assert param["data_status"] in ["LIVE", "FORECAST", "CACHED", "HISTORICAL"]
        assert param["confidence"] > 0
        assert param["source"] in ["INCOIS", "IMD", "MOSDAC", "ISRO-MOSDAC", "Open-Meteo", "GDACS", "stormglass"]


@pytest.mark.asyncio
@respx.mock
async def test_mangalore_what_if_query_e2e(monkeypatch):
    _mock_connectors(monkeypatch)
    monkeypatch.setattr(
        graph_module, "create_plan",
        AsyncMock(return_value={
            "intent": "what-if alternative departure",
            "place_name": "Mangaluru",
            "target_time": "06:00",
            "is_what_if": True,
            "alternative_time": "11:00",
            "agents": ["weather", "risk"],
            "response_language": "English",
        }),
    )
    monkeypatch.setattr(
        graph_module, "synthesize_answer",
        AsyncMock(return_value="RECOMMENDATION: CONDITIONS WORSEN AT 11 AM. Risk Score rises to 58/100 (HIGH)."),
    )

    graph = build_graph(client=object())

    # Query 2: What if I leave at 11 AM instead?
    history = [
        {"role": "user", "content": "Can I go fishing near Mangaluru tomorrow at 6 AM?"},
        {
            "role": "assistant",
            "content": "Conditions are moderate at 6 AM with 1.3m waves and 12 knots wind.",
        },
    ]

    state = await graph.ainvoke({
        "message": "What if I leave at 11 AM instead?",
        "history": history,
    })

    assert state.get("final_answer") is not None
    assert "what_if_result" in state
    what_if = state["what_if_result"]
    assert what_if is not None
    assert what_if["original_time"] == "06:00"
    assert what_if["alternative_time"] == "11:00"
    assert 0 <= what_if["original_risk_score"] <= 100
    assert 0 <= what_if["alternative_risk_score"] <= 100
    assert len(what_if["differences"]) > 0
    assert what_if["verdict"] != ""
