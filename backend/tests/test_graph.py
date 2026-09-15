from datetime import datetime, timezone
from unittest.mock import AsyncMock
from app import graph as graph_module
from app.schemas import TraceEntry


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


async def test_graph_falls_back_to_default_plan_when_planner_fails(monkeypatch):
    monkeypatch.setattr(graph_module, "create_plan", AsyncMock(side_effect=RuntimeError("LLM down")))
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock())

    compiled = graph_module.build_graph(client=object())
    result = await compiled.ainvoke({"message": "is it safe?", "history": []})

    assert result["plan"]["place_name"] is None
    assert "location" in result["final_answer"].lower()
