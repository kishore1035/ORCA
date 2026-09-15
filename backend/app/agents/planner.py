# backend/app/agents/planner.py
from pydantic import BaseModel
from app.llm import DEFAULT_MODEL


class PlanSchema(BaseModel):
    intent: str
    place_name: str | None
    agents: list[str]
    response_language: str


PLANNER_SYSTEM_PROMPT = """You are the planning agent for a marine intelligence assistant used by
fishermen and coastal stakeholders. Given the user's message and conversation history, decide:
- their intent, in one short phrase
- the place/location they mean (reuse the location from earlier turns if this message is a
  follow-up like "what about tomorrow?" that doesn't repeat it); null if genuinely no location
  has ever been given
- which specialist agents are needed, from: "weather" (wind/wave/swell), "ocean_analytics"
  (SST/chlorophyll/fishing-zone likelihood), "risk" (safety go/no-go, alerts), "geospatial"
  (location resolution, protected-area/boundary proximity)
- the language to respond in, matching the user's own message

Respond only with the requested JSON fields."""


async def create_plan(client, message: str, history: list[dict]) -> dict:
    history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history)
    prompt = (
        f"{PLANNER_SYSTEM_PROMPT}\n\nConversation so far:\n{history_text}\n\n"
        f"User message: {message}"
    )
    response = await client.aio.models.generate_content(
        model=DEFAULT_MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json", "response_schema": PlanSchema},
    )
    plan = PlanSchema.model_validate_json(response.text)
    return plan.model_dump()
