import pytest
from app.agents.verification_agent import audit_marine_evidence, run_verification_agent
from app.schemas import VerificationResult


def test_audit_marine_evidence_passes_valid_data():
    evidence = [
        {
            "parameter": "significant_wave_height",
            "value": 2.3,
            "unit": "m",
            "timestamp": "2026-09-16T06:00:00Z",
            "valid_from": "2026-09-16T05:00:00Z",
            "valid_until": "2026-09-16T07:00:00Z",
            "source": "INCOIS",
            "data_status": "FORECAST",
        },
        {
            "parameter": "wind_speed",
            "value": 28.5,
            "unit": "km/h",
            "timestamp": "2026-09-16T06:00:00Z",
            "valid_from": "2026-09-16T05:00:00Z",
            "valid_until": "2026-09-16T07:00:00Z",
            "source": "INCOIS",
            "data_status": "FORECAST",
        },
    ]
    sources = ["INCOIS", "IMD"]
    res = audit_marine_evidence(evidence, sources)
    assert isinstance(res, VerificationResult)
    assert res.is_verified is True
    assert res.data_status == "FORECAST"
    assert len(res.checks_passed) >= 3
    assert len(res.issues) == 0


def test_audit_marine_evidence_flags_insufficient_data():
    res = audit_marine_evidence([], ["INCOIS"])
    assert res.is_verified is False
    assert "insufficient" in res.issues[0].lower()


def test_audit_marine_evidence_flags_unexpected_units():
    evidence = [
        {
            "parameter": "significant_wave_height",
            "value": 2.3,
            "unit": "feet",  # unexpected unit
            "timestamp": "2026-09-16T06:00:00Z",
            "source": "INCOIS",
            "data_status": "FORECAST",
        }
    ]
    res = audit_marine_evidence(evidence, ["INCOIS"])
    assert res.is_verified is False
    assert any("unexpected unit" in issue.lower() for issue in res.issues)


@pytest.mark.asyncio
async def test_run_verification_agent_returns_trace():
    evidence = [
        {
            "parameter": "significant_wave_height",
            "value": 1.5,
            "unit": "m",
            "timestamp": "2026-09-16T06:00:00Z",
            "source": "INCOIS",
            "data_status": "FORECAST",
        }
    ]
    output, trace = await run_verification_agent(evidence, ["INCOIS"])
    assert output["is_verified"] is True
    assert trace.agent == "verification"
    assert trace.sources == ["INCOIS"]
