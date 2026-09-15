from unittest.mock import AsyncMock
from app.agents.reporting_agent import synthesize_answer


async def test_synthesize_answer_returns_llm_text():
    fake_client = type("Client", (), {})()
    fake_client.generate_text = AsyncMock(return_value="It is safe to go out tomorrow morning.")

    answer = await synthesize_answer(
        fake_client,
        user_message="is it safe tomorrow?",
        response_language="English",
        agent_results={"risk_result": {"verdict": "safe", "reasons": ["calm seas"]}},
    )

    assert answer == "It is safe to go out tomorrow morning."
    fake_client.generate_text.assert_awaited_once()
