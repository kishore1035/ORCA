# backend/app/graph.py
import logging
from typing import TypedDict, Any
from langgraph.graph import StateGraph, END
from app.agents.planner import create_plan
from app.agents.weather_agent import run_weather_agent
from app.agents.ocean_analytics_agent import run_ocean_analytics_agent
from app.agents.risk_agent import run_risk_agent
from app.agents.geospatial_agent import run_geospatial_agent
from app.agents.route_agent import run_route_agent
from app.agents.reporting_agent import synthesize_answer
from app.agents.verification_agent import audit_marine_evidence
from app.agents.what_if_agent import run_what_if_agent
from app.connectors.geospatial import geocode
from app.schemas import TraceEntry

NO_LOCATION_ANSWER = "I need a location to answer that -- which coast, port, or coordinates should I check?"

logger = logging.getLogger(__name__)


class GraphState(TypedDict, total=False):
    message: str
    history: list[dict]
    plan: dict
    lat: float
    lon: float
    location: dict | None
    canonical_location: dict | None
    weather_result: dict
    ocean_result: dict
    risk_result: dict
    geo_result: dict
    route_result: dict
    verification_result: dict
    what_if_result: dict
    evidence: list[dict[str, Any]]
    trace: list[TraceEntry]
    final_answer: str


DEFAULT_PLAN = {
    "intent": "general marine query",
    "place_name": None,
    "start_place_name": None,
    "end_place_name": None,
    "target_time": None,
    "is_what_if": False,
    "alternative_time": None,
    "is_spatial_what_if": False,
    "move_distance_km": None,
    "move_direction": None,
    "task": "general",
    "agents": ["weather"],
    "response_language": "English",
}


async def planner_node(state: GraphState) -> GraphState:
    try:
        plan = await create_plan(state["_client"], state["message"], state.get("history", []))
    except Exception as exc:
        logger.warning("planner create_plan failed, falling back to default plan: %s", exc)
        plan = dict(DEFAULT_PLAN)
    trace_entry = TraceEntry(
        agent="planner",
        inputs={"message": state["message"]},
        output=plan,
        sources=[],
    )
    return {**state, "plan": plan, "trace": [trace_entry], "evidence": []}


async def geospatial_node(state: GraphState) -> GraphState:
    loc = state.get("location")
    if loc and "latitude" in loc and "longitude" in loc:
        coords = (float(loc["latitude"]), float(loc["longitude"]))
        output, trace = await run_geospatial_agent(coords=coords, location_metadata=loc)
    else:
        output, trace = await run_geospatial_agent(place_name=state["plan"]["place_name"])

    canonical_loc = {
        "latitude": output["lat"],
        "longitude": output["lon"],
        "display_name": output.get("resolved_name"),
        "district": output.get("nearest_coastal_name"),
        "state": output.get("nearest_coastal_sector"),
        "country": "India",
        "source": loc.get("source", "COORDINATES") if loc else "MANUAL",
        "distance_to_coast_km": output.get("distance_to_coast_km"),
        "is_offshore": output.get("is_offshore", True),
        "nearest_coastal_point": output.get("nearest_coastal_point"),
        "in_marine_coverage": output.get("in_marine_coverage", True),
        "coverage_message": output.get("coverage_message"),
    }

    return {
        **state,
        "lat": output["lat"],
        "lon": output["lon"],
        "geo_result": output,
        "canonical_location": canonical_loc,
        "trace": state["trace"] + [trace],
    }


async def weather_node(state: GraphState) -> GraphState:
    target_time = state.get("plan", {}).get("target_time")
    output, trace = await run_weather_agent(state["lat"], state["lon"], target_time=target_time)
    evidence = list(state.get("evidence", []))
    if "parameters" in output:
        evidence.extend(output["parameters"])
    canonical_loc = dict(state.get("canonical_location") or {})
    if output.get("grid_distance_km") is not None:
        canonical_loc["grid_distance_km"] = output["grid_distance_km"]
    return {
        **state,
        "weather_result": output,
        "evidence": evidence,
        "canonical_location": canonical_loc,
        "trace": state["trace"] + [trace],
    }


async def risk_node(state: GraphState) -> GraphState:
    output, trace = await run_risk_agent(
        state["lat"], state["lon"], state["weather_result"], state.get("geo_result")
    )
    return {**state, "risk_result": output, "trace": state["trace"] + [trace]}


async def ocean_analytics_node(state: GraphState) -> GraphState:
    output, trace = await run_ocean_analytics_agent(state["lat"], state["lon"])
    evidence = list(state.get("evidence", []))
    if "parameters" in output:
        evidence.extend(output["parameters"])
    return {**state, "ocean_result": output, "evidence": evidence, "trace": state["trace"] + [trace]}


async def route_node(state: GraphState) -> GraphState:
    plan = state["plan"]
    start = await geocode(plan["start_place_name"])
    end = await geocode(plan["end_place_name"])
    output, trace = await run_route_agent(
        start.data["lat"], start.data["lon"], end.data["lat"], end.data["lon"]
    )
    return {**state, "route_result": output, "trace": state["trace"] + [trace]}


def _is_real_place(name) -> bool:
    """LLMs occasionally emit 'null' or 'none' instead of real JSON null."""
    return bool(name) and str(name).strip().lower() not in ("", "null", "none")


_RESULT_KEY_TO_TRACE_AGENT = {
    "geo_result": "geospatial",
    "weather_result": "weather",
    "ocean_result": "ocean_analytics",
    "risk_result": "risk",
    "route_result": "route",
}


async def reporting_node(state: GraphState) -> GraphState:
    plan = state["plan"]
    has_route = _is_real_place(plan.get("start_place_name")) and _is_real_place(plan.get("end_place_name"))
    has_loc = _is_real_place(plan.get("place_name")) or state.get("location") is not None or ("lat" in state and "lon" in state)
    if not has_loc and not has_route:
        return {**state, "final_answer": NO_LOCATION_ANSWER}

    trace_by_agent = {entry.agent: entry for entry in state["trace"]}
    agent_results = {}
    for key, agent_name in _RESULT_KEY_TO_TRACE_AGENT.items():
        if not state.get(key):
            continue
        entry = trace_by_agent.get(agent_name)
        agent_results[key] = {
            **state[key],
            "_sources": entry.sources if entry else [],
            "_fetched_at": entry.fetched_at.isoformat() if entry and entry.fetched_at else None,
            "_is_cached": entry.is_cached if entry else False,
        }

    # 1. Audit evidence with Verification Agent
    all_sources = []
    for entry in state.get("trace", []):
        all_sources.extend(entry.sources)
    evidence_list = state.get("evidence", [])
    verification_res = audit_marine_evidence(evidence_list, all_sources)
    verification_dict = verification_res.model_dump()
    agent_results["verification_result"] = verification_dict

    # 2. Dynamic What-If analysis when alternative departure time or spatial relocation requested
    what_if_dict = None
    msg_lower = state["message"].lower()
    is_spatial = bool(plan.get("is_spatial_what_if")) or ("move" in msg_lower and "km" in msg_lower)
    is_what_if = plan.get("is_what_if") or "what if" in msg_lower or "instead" in msg_lower or is_spatial
    if is_what_if and "lat" in state and "lon" in state:
        orig_time = "06:00"
        alt_time = plan.get("alternative_time") or ("11:00" if "11" in msg_lower else "11:00")
        
        move_dist = plan.get("move_distance_km")
        if not move_dist and "km" in msg_lower:
            import re
            m = re.search(r"(\d+(\.\d+)?)\s*km", msg_lower)
            if m:
                move_dist = float(m.group(1))
        
        move_dir = plan.get("move_direction")
        if not move_dir:
            for d in ["south", "north", "east", "west", "offshore"]:
                if d in msg_lower:
                    move_dir = d
                    break

        try:
            warning_level = state.get("weather_result", {}).get("warning_level")
            what_if_dict, _ = await run_what_if_agent(
                state["lat"],
                state["lon"],
                original_time=orig_time,
                alternative_time=alt_time,
                imd_warning_level=warning_level,
                is_spatial=is_spatial,
                move_distance_km=move_dist,
                move_direction=move_dir,
            )
            agent_results["what_if_result"] = what_if_dict
        except Exception:
            pass

    answer = await synthesize_answer(
        state["_client"], state["message"], plan["response_language"], agent_results
    )
    return {
        **state,
        "final_answer": answer,
        "verification_result": verification_dict,
        "what_if_result": what_if_dict,
    }


def _route_after_planner(state: GraphState) -> str:
    plan = state["plan"]
    if _is_real_place(plan.get("start_place_name")) and _is_real_place(plan.get("end_place_name")):
        return "route"
    if _is_real_place(plan.get("place_name")) or state.get("location") is not None or ("lat" in state and "lon" in state):
        return "geospatial"
    return "reporting"



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
    graph.add_node("route", route_node)
    graph.add_node("reporting", reporting_with_client)

    graph.set_entry_point("planner")
    graph.add_conditional_edges(
        "planner",
        _route_after_planner,
        {"geospatial": "geospatial", "route": "route", "reporting": "reporting"},
    )
    graph.add_edge("geospatial", "weather")
    graph.add_edge("weather", "risk")
    graph.add_edge("risk", "ocean_analytics")
    graph.add_edge("ocean_analytics", "reporting")
    graph.add_edge("route", "reporting")
    graph.add_edge("reporting", END)
    return graph.compile()
