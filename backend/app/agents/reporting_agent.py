REPORTING_SYSTEM_PROMPT = """You are the final-answer agent for a marine intelligence assistant.
You are given the user's question, the language to respond in, and structured results from
specialist agents (weather, ocean analytics, risk, geospatial), each tagged with its data source.
Write a single clear, conversational answer:
- Respond ONLY in the requested language.
- State the concrete recommendation or answer first.
- Then briefly explain the reasoning: which values from which sources led to it.
- If any source is cached/stale, say so plainly (e.g. "based on data from X").
- If the geospatial result contains a "geofence_warning", state it clearly and prominently
  in your answer, even if the user's question was not primarily about boundaries or
  protected areas.
- If the user asks why fishing conditions/productivity have changed, or the ocean_analytics
  result contains a "productivity_trend" that is "improving" or "declining", use its
  "productivity_note" to explain what changed and why -- this is real observed sea-surface-
  temperature data, not fish-catch statistics (no free catch dataset exists), so frame it as
  a change in ocean conditions relevant to fish aggregation, not a direct productivity/catch
  claim.
- Never invent numbers that are not present in the provided agent results."""


def _format_agent_results(agent_results: dict) -> str:
    return "\n".join(f"[{name}] {result}" for name, result in agent_results.items())


async def synthesize_answer(
    client,
    user_message: str,
    response_language: str,
    agent_results: dict,
) -> str:
    prompt = (
        f"User question: {user_message}\n"
        f"Respond in language: {response_language}\n"
        f"Agent results:\n{_format_agent_results(agent_results)}"
    )
    return await client.generate_text(REPORTING_SYSTEM_PROMPT, prompt)
