# backend/app/agents/planner.py
from pydantic import BaseModel

PLAN_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "place_name": {"type": ["string", "null"]},
        "start_place_name": {"type": ["string", "null"]},
        "end_place_name": {"type": ["string", "null"]},
        "target_time": {"type": ["string", "null"]},
        "is_what_if": {"type": "boolean"},
        "alternative_time": {"type": ["string", "null"]},
        "is_spatial_what_if": {"type": "boolean"},
        "move_distance_km": {"type": ["number", "null"]},
        "move_direction": {"type": ["string", "null"]},
        "task": {"type": "string"},
        "agents": {"type": "array", "items": {"type": "string"}},
        "response_language": {"type": "string"},
    },
    "required": [
        "intent", "place_name", "start_place_name", "end_place_name", "agents", "response_language",
    ],
    "additionalProperties": False,
}


class PlanSchema(BaseModel):
    intent: str
    place_name: str | None
    start_place_name: str | None = None
    end_place_name: str | None = None
    target_time: str | None = None
    is_what_if: bool = False
    alternative_time: str | None = None
    is_spatial_what_if: bool = False
    move_distance_km: float | None = None
    move_direction: str | None = None
    task: str = "general"
    agents: list[str]
    response_language: str


PLANNER_SYSTEM_PROMPT = """You are the planning agent for a marine intelligence assistant used by
fishermen and coastal stakeholders. Given the user's message and conversation history, decide:
- their intent, in one short phrase
- the place/location they mean (reuse the location from earlier turns if this message is a
  follow-up like "what about tomorrow?" that doesn't repeat it); null if genuinely no location
  has ever been given
- start_place_name and end_place_name: ONLY when the user is asking about a ROUTE or the safest
  way to travel BETWEEN two named places (e.g. "safest route from Kochi to Alappuzha"). Both null
  for every other query.
- target_time: date/time mentioned by the user (e.g. "tomorrow at 6 AM", "06:00", "tomorrow morning"); null if unspecified.
- is_what_if: true if the query is asking "what if" or proposing an alternative departure/time/route (e.g. "what if I leave at 11 AM instead?" or "what if I move 15 km south?").
- alternative_time: proposed alternative time (e.g. "11:00" or "11 AM"); null if not a time what-if query.
- is_spatial_what_if: true if the user asks about moving or relocating location (e.g. "what if I move 15 km south?").
- move_distance_km: numerical distance in km to move (e.g. 15.0); null if not moving.
- move_direction: direction of movement (e.g. "south", "north", "east", "west", "offshore"); null if not moving.
- task: "fishing", "navigation", "weather", "hazard", or "general".
- which specialist agents are needed:
  - "weather" (wind/wave/swell/currents from INCOIS and IMD)
  - "ocean_analytics" (SST/chlorophyll/PFZ advisory-aware analysis from INCOIS and ISRO-MOSDAC)
  - "risk" (deterministic safety go/no-go, hazard factors)
  - "geospatial" (location resolution, protected-area proximity)
- the language to respond in, matching the user's own message

Respond only with the requested JSON fields."""


async def create_plan(client, message: str, history: list[dict]) -> dict:
    history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history)
    prompt = f"Conversation so far:\n{history_text}\n\nUser message: {message}"
    plan_dict = await client.generate_structured(
        PLANNER_SYSTEM_PROMPT, prompt, PLAN_JSON_SCHEMA
    )
    plan = PlanSchema.model_validate(plan_dict)
    return plan.model_dump()
