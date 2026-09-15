import httpx
import respx
from unittest.mock import AsyncMock
from app.graph import build_graph
from app import graph as graph_module


def _mock_all_connectors():
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(
            200, json=[{"lat": "9.93", "lon": "76.27", "display_name": "Kochi, Kerala, India"}]
        )
    )
    respx.get("https://marine-api.open-meteo.com/v1/marine").mock(
        return_value=httpx.Response(200, json={"hourly": {"wave_height": [1.0], "swell_wave_height": [0.5]}})
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(
            200, json={"hourly": {"wind_speed_10m": [15.0], "wind_direction_10m": [200], "time": ["2026-09-15T06:00"]}}
        )
    )
    respx.get(url__regex=r"jplMURSST41\.json").mock(
        return_value=httpx.Response(200, json={"table": {"rows": [["t", 9.93, 76.27, 28.5]]}})
    )
    respx.get(url__regex=r"erdMH1chla1day\.json").mock(
        return_value=httpx.Response(200, json={"table": {"rows": [["t", 9.93, 76.27, 0.35]]}})
    )
    respx.get(url__regex=r"gdacs\.org/gdacsapi/api/events/geteventlist/SEARCH").mock(
        return_value=httpx.Response(200, json={"features": []})
    )


def _fake_plan(intent: str, agents: list[str]) -> dict:
    return {"intent": intent, "place_name": "Kochi", "agents": agents, "response_language": "English"}


@respx.mock
async def test_is_it_safe_query_flags_calm_conditions(monkeypatch):
    _mock_all_connectors()
    monkeypatch.setattr(
        graph_module, "create_plan", AsyncMock(return_value=_fake_plan("safety check", ["weather", "risk"]))
    )
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock(return_value="Safe to go out."))

    graph = build_graph(client=object())
    result = await graph.ainvoke({"message": "is it safe near Kochi tomorrow?", "history": []})

    assert result["risk_result"]["verdict"] == "safe"
    assert result["final_answer"] == "Safe to go out."
    assert [t.agent for t in result["trace"]] == ["planner", "geospatial", "weather", "risk", "ocean_analytics"]


@respx.mock
async def test_fishing_zone_query_produces_pfz_likelihood(monkeypatch):
    _mock_all_connectors()
    monkeypatch.setattr(
        graph_module, "create_plan", AsyncMock(return_value=_fake_plan("find PFZ", ["ocean_analytics"]))
    )
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock(return_value="Good fishing zone nearby."))

    graph = build_graph(client=object())
    result = await graph.ainvoke({"message": "where is the nearest fishing zone near Kochi?", "history": []})

    assert result["ocean_result"]["pfz_likelihood"] == "high"


@respx.mock
async def test_alerts_query_reports_no_active_alerts(monkeypatch):
    _mock_all_connectors()
    monkeypatch.setattr(
        graph_module, "create_plan", AsyncMock(return_value=_fake_plan("check alerts", ["risk"]))
    )
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock(return_value="No alerts."))

    graph = build_graph(client=object())
    result = await graph.ainvoke({"message": "any cyclone alerts near Kochi?", "history": []})

    assert result["risk_result"]["reasons"] == [
        "No hazardous conditions found in wave, wind, cyclone, or lightning data"
    ]


@respx.mock
async def test_followup_query_reuses_location_from_plan(monkeypatch):
    _mock_all_connectors()
    monkeypatch.setattr(
        graph_module, "create_plan",
        AsyncMock(return_value=_fake_plan("safety check for later date", ["weather", "risk"])),
    )
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock(return_value="Still safe Thursday."))

    graph = build_graph(client=object())
    history = [
        {"role": "user", "content": "is it safe near Kochi tomorrow?"},
        {"role": "assistant", "content": "Safe to go out."},
    ]
    result = await graph.ainvoke({"message": "what about Thursday instead?", "history": history})

    assert result["final_answer"] == "Still safe Thursday."
