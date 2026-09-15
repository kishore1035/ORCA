from unittest.mock import AsyncMock
from app.agents.planner import create_plan, PlanSchema


async def test_create_plan_parses_structured_response():
    fake_plan = PlanSchema(
        intent="check safety",
        place_name="Kochi",
        agents=["weather", "risk"],
        response_language="English",
    )
    fake_response = type("Resp", (), {"text": fake_plan.model_dump_json()})()
    fake_client = type("Client", (), {})()
    fake_client.aio = type("Aio", (), {})()
    fake_client.aio.models = type("Models", (), {})()
    fake_client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    plan = await create_plan(fake_client, "is it safe near Kochi tomorrow?", [])

    assert plan["intent"] == "check safety"
    assert plan["place_name"] == "Kochi"
    assert plan["agents"] == ["weather", "risk"]
    fake_client.aio.models.generate_content.assert_awaited_once()
