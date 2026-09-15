from unittest.mock import AsyncMock
from app.agents.planner import create_plan


async def test_create_plan_parses_structured_response():
    fake_client = type("Client", (), {})()
    fake_client.generate_structured = AsyncMock(
        return_value={
            "intent": "check safety",
            "place_name": "Kochi",
            "agents": ["weather", "risk"],
            "response_language": "English",
        }
    )

    plan = await create_plan(fake_client, "is it safe near Kochi tomorrow?", [])

    assert plan["intent"] == "check safety"
    assert plan["place_name"] == "Kochi"
    assert plan["agents"] == ["weather", "risk"]
    fake_client.generate_structured.assert_awaited_once()
