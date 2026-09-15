from datetime import datetime, timezone
from unittest.mock import AsyncMock
from app import graph as graph_module
from app.schemas import ConnectorResult, TraceEntry


def _trace(agent_name: str) -> TraceEntry:
    return TraceEntry(
        agent=agent_name, inputs={}, output={}, sources=["test"],
        fetched_at=datetime.now(timezone.utc), is_cached=False,
    )


async def test_graph_runs_full_pipeline_when_location_present(monkeypatch):
    monkeypatch.setattr(
        graph_module, "create_plan",
        AsyncMock(return_value={
            "intent": "check safety", "place_name": "Kochi",
            "agents": ["weather", "risk"], "response_language": "English",
        }),
    )
    monkeypatch.setattr(
        graph_module, "run_geospatial_agent",
        AsyncMock(return_value=({"lat": 9.9, "lon": 76.2}, _trace("geospatial"))),
    )
    monkeypatch.setattr(
        graph_module, "run_weather_agent",
        AsyncMock(return_value=({"wave_height_m": 1.0, "wind_speed_kmh": 10.0}, _trace("weather"))),
    )
    monkeypatch.setattr(
        graph_module, "run_risk_agent",
        AsyncMock(return_value=({"verdict": "safe", "reasons": []}, _trace("risk"))),
    )
    monkeypatch.setattr(
        graph_module, "run_ocean_analytics_agent",
        AsyncMock(return_value=({"pfz_likelihood": "moderate"}, _trace("ocean_analytics"))),
    )
    monkeypatch.setattr(
        graph_module, "synthesize_answer", AsyncMock(return_value="It is safe to go out.")
    )

    compiled = graph_module.build_graph(client=object())
    result = await compiled.ainvoke({"message": "is it safe near Kochi?", "history": []})

    trace_agents = [t.agent for t in result["trace"]]
    assert trace_agents == ["planner", "geospatial", "weather", "risk", "ocean_analytics"]
    assert result["final_answer"] == "It is safe to go out."


async def test_graph_asks_for_location_when_none_given(monkeypatch):
    monkeypatch.setattr(
        graph_module, "create_plan",
        AsyncMock(return_value={
            "intent": "check safety", "place_name": None,
            "agents": [], "response_language": "English",
        }),
    )
    geospatial_mock = AsyncMock()
    monkeypatch.setattr(graph_module, "run_geospatial_agent", geospatial_mock)
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock())

    compiled = graph_module.build_graph(client=object())
    result = await compiled.ainvoke({"message": "is it safe?", "history": []})

    geospatial_mock.assert_not_awaited()
    assert "location" in result["final_answer"].lower()


async def test_graph_falls_back_to_default_plan_when_planner_fails(monkeypatch, caplog):
    monkeypatch.setattr(graph_module, "create_plan", AsyncMock(side_effect=RuntimeError("LLM down")))
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock())

    compiled = graph_module.build_graph(client=object())
    with caplog.at_level("WARNING", logger="app.graph"):
        result = await compiled.ainvoke({"message": "is it safe?", "history": []})

    assert result["plan"]["place_name"] is None
    assert "location" in result["final_answer"].lower()
    assert any("planner create_plan failed" in record.message for record in caplog.records)


async def test_reporting_node_passes_staleness_info_to_synthesize_answer(monkeypatch):
    monkeypatch.setattr(
        graph_module, "create_plan",
        AsyncMock(return_value={
            "intent": "check safety", "place_name": "Kochi",
            "agents": ["weather", "risk"], "response_language": "English",
        }),
    )
    monkeypatch.setattr(
        graph_module, "run_geospatial_agent",
        AsyncMock(return_value=({"lat": 9.9, "lon": 76.2}, _trace("geospatial"))),
    )
    stale_weather_trace = TraceEntry(
        agent="weather", inputs={}, output={}, sources=["cache"],
        fetched_at=datetime(2026, 9, 10, tzinfo=timezone.utc), is_cached=True,
    )
    monkeypatch.setattr(
        graph_module, "run_weather_agent",
        AsyncMock(return_value=({"wave_height_m": 1.0, "wind_speed_kmh": 10.0}, stale_weather_trace)),
    )
    monkeypatch.setattr(
        graph_module, "run_risk_agent",
        AsyncMock(return_value=({"verdict": "safe", "reasons": []}, _trace("risk"))),
    )
    monkeypatch.setattr(
        graph_module, "run_ocean_analytics_agent",
        AsyncMock(return_value=({"pfz_likelihood": "moderate"}, _trace("ocean_analytics"))),
    )
    synthesize_mock = AsyncMock(return_value="It is safe to go out.")
    monkeypatch.setattr(graph_module, "synthesize_answer", synthesize_mock)

    compiled = graph_module.build_graph(client=object())
    await compiled.ainvoke({"message": "is it safe near Kochi?", "history": []})

    _, _, _, agent_results = synthesize_mock.await_args.args
    assert agent_results["weather_result"]["_is_cached"] is True
    assert agent_results["weather_result"]["_fetched_at"] == "2026-09-10T00:00:00+00:00"
    assert agent_results["risk_result"]["_is_cached"] is False


async def test_graph_routes_to_route_node_when_start_and_end_given(monkeypatch):
    monkeypatch.setattr(
        graph_module, "create_plan",
        AsyncMock(return_value={
            "intent": "safest route", "place_name": None,
            "start_place_name": "Kochi", "end_place_name": "Alappuzha",
            "agents": [], "response_language": "English",
        }),
    )

    def fake_geocode(place_name):
        coords = {"Kochi": (9.97, 76.24), "Alappuzha": (9.49, 76.33)}
        lat, lon = coords[place_name]
        return ConnectorResult(
            data={"lat": lat, "lon": lon, "display_name": place_name},
            source="nominatim", fetched_at=datetime.now(timezone.utc), is_cached=False,
        )

    monkeypatch.setattr(graph_module, "geocode", AsyncMock(side_effect=fake_geocode))
    monkeypatch.setattr(
        graph_module, "run_route_agent",
        AsyncMock(return_value=(
            {"waypoints": [], "overall_verdict": "safe"}, _trace("route"),
        )),
    )
    geospatial_mock = AsyncMock()
    monkeypatch.setattr(graph_module, "run_geospatial_agent", geospatial_mock)
    synthesize_mock = AsyncMock(return_value="The route is safe.")
    monkeypatch.setattr(graph_module, "synthesize_answer", synthesize_mock)

    compiled = graph_module.build_graph(client=object())
    result = await compiled.ainvoke(
        {"message": "what's the safest route from Kochi to Alappuzha?", "history": []}
    )

    geospatial_mock.assert_not_awaited()
    assert [t.agent for t in result["trace"]] == ["planner", "route"]
    assert result["route_result"]["overall_verdict"] == "safe"
    assert result["final_answer"] == "The route is safe."
    _, _, _, agent_results = synthesize_mock.await_args.args
    assert "route_result" in agent_results
