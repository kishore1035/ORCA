from unittest.mock import AsyncMock
from app.agents.reporting_agent import synthesize_answer


async def test_synthesize_answer_returns_llm_text():
    fake_response = type("Resp", (), {"text": "It is safe to go out tomorrow morning."})()
    fake_client = type("Client", (), {})()
    fake_client.aio = type("Aio", (), {})()
    fake_client.aio.models = type("Models", (), {})()
    fake_client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    answer = await synthesize_answer(
        fake_client,
        user_message="is it safe tomorrow?",
        response_language="English",
        agent_results={"risk_result": {"verdict": "safe", "reasons": ["calm seas"]}},
    )

    assert answer == "It is safe to go out tomorrow morning."
    fake_client.aio.models.generate_content.assert_awaited_once()
