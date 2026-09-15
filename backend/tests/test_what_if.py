import pytest
from app.agents.what_if_agent import run_what_if_agent
from app.schemas import WhatIfComparison


@pytest.mark.asyncio
async def test_what_if_agent_computes_risk_delta():
    # Mangaluru coordinates
    lat, lon = 12.9141, 74.8560
    output, trace = await run_what_if_agent(
        lat, lon, original_time="06:00", alternative_time="11:00", imd_warning_level="Yellow"
    )

    comparison = WhatIfComparison.model_validate(output)
    assert comparison.original_time == "06:00"
    assert comparison.alternative_time == "11:00"

    # Original risk (06:00) should be higher than alternative (11:00)
    assert comparison.original_risk_score > comparison.alternative_risk_score
    assert len(comparison.differences) >= 2
    assert "reduces marine risk" in comparison.verdict.lower()
    assert trace.agent == "what_if"
