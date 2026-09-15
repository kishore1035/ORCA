# backend/app/agents/planner.py
from pydantic import BaseModel

PLAN_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string"},
        "place_name": {"type": ["string", "null"]},
        "start_place_name": {"type": ["string", "null"]},
        "end_place_name": {"type": ["string", "null"]},
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
  for every other query, including single-location queries -- do not populate these unless the
  message names two distinct places connected by travel/route intent.
- which specialist agents are needed, from: "weather" (wind/wave/swell), "ocean_analytics"
  (SST/chlorophyll/fishing-zone likelihood), "risk" (safety go/no-go, alerts), "geospatial"
  (location resolution, protected-area/boundary proximity)
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
