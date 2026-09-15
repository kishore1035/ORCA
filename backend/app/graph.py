from typing import TypedDict
from langgraph.graph import StateGraph, END
from app.agents.planner import create_plan
from app.agents.weather_agent import run_weather_agent
from app.agents.ocean_analytics_agent import run_ocean_analytics_agent
from app.agents.risk_agent import run_risk_agent
from app.agents.geospatial_agent import run_geospatial_agent
from app.agents.reporting_agent import synthesize_answer
from app.schemas import TraceEntry

NO_LOCATION_ANSWER = "I need a location to answer that -- which coast, port, or coordinates should I check?"


class GraphState(TypedDict, total=False):
    message: str
    history: list[dict]
    plan: dict
    lat: float
    lon: float
    weather_result: dict
    ocean_result: dict
    risk_result: dict
    geo_result: dict
    trace: list[TraceEntry]
    final_answer: str


DEFAULT_PLAN = {
    "intent": "general marine query",
    "place_name": None,
    "agents": ["weather"],
    "response_language": "English",
}


async def planner_node(state: GraphState) -> GraphState:
    try:
        plan = await create_plan(state["_client"], state["message"], state.get("history", []))
    except Exception:
        plan = dict(DEFAULT_PLAN)
    trace_entry = TraceEntry(
        agent="planner",
        inputs={"message": state["message"]},
        output=plan,
        sources=[],
    )
    return {**state, "plan": plan, "trace": [trace_entry]}


async def geospatial_node(state: GraphState) -> GraphState:
    output, trace = await run_geospatial_agent(state["plan"]["place_name"])
    return {
        **state,
        "lat": output["lat"],
        "lon": output["lon"],
        "geo_result": output,
        "trace": state["trace"] + [trace],
    }


async def weather_node(state: GraphState) -> GraphState:
    output, trace = await run_weather_agent(state["lat"], state["lon"])
    return {**state, "weather_result": output, "trace": state["trace"] + [trace]}


async def risk_node(state: GraphState) -> GraphState:
    output, trace = await run_risk_agent(state["lat"], state["lon"], state["weather_result"])
    return {**state, "risk_result": output, "trace": state["trace"] + [trace]}


async def ocean_analytics_node(state: GraphState) -> GraphState:
    output, trace = await run_ocean_analytics_agent(state["lat"], state["lon"])
    return {**state, "ocean_result": output, "trace": state["trace"] + [trace]}


async def reporting_node(state: GraphState) -> GraphState:
    if not state["plan"].get("place_name"):
        return {**state, "final_answer": NO_LOCATION_ANSWER}
    agent_results = {
        key: state[key]
        for key in ("geo_result", "weather_result", "ocean_result", "risk_result")
        if state.get(key)
    }
    answer = await synthesize_answer(
        state["_client"], state["message"], state["plan"]["response_language"], agent_results
    )
    return {**state, "final_answer": answer}


def _route_after_planner(state: GraphState) -> str:
    return "geospatial" if state["plan"].get("place_name") else "reporting"


def build_graph(client):
    graph = StateGraph(GraphState)

    async def planner_with_client(state: GraphState) -> GraphState:
        return await planner_node({**state, "_client": client})

    async def reporting_with_client(state: GraphState) -> GraphState:
        return await reporting_node({**state, "_client": client})

    graph.add_node("planner", planner_with_client)
    graph.add_node("geospatial", geospatial_node)
    graph.add_node("weather", weather_node)
    graph.add_node("risk", risk_node)
    graph.add_node("ocean_analytics", ocean_analytics_node)
    graph.add_node("reporting", reporting_with_client)

    graph.set_entry_point("planner")
    graph.add_conditional_edges(
        "planner", _route_after_planner, {"geospatial": "geospatial", "reporting": "reporting"}
    )
    graph.add_edge("geospatial", "weather")
    graph.add_edge("weather", "risk")
    graph.add_edge("risk", "ocean_analytics")
    graph.add_edge("ocean_analytics", "reporting")
    graph.add_edge("reporting", END)
    return graph.compile()
