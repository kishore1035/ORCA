# backend/tests/test_hazard_simulation.py
import pytest
from app.agents.risk_engine import calculate_risk
from app.schemas import RiskAssessment


def test_simulate_low_risk_calm_conditions():
    """Simulate calm coastal conditions (e.g. Kochi Munambam)."""
    assessment = calculate_risk(
        wave_height_m=0.8,
        wind_speed_kmh=11.5,
        wave_period_s=8.5,
        swell_height_m=0.6,
        surface_current_ms=0.22,
        imd_warning_level="Green",
        target_time="06:00",
    )
    assert assessment.risk_level == "LOW"
    assert assessment.risk_score < 35
    assert "approves departure" in assessment.recommendation.lower()
    assert any("wave height 0.8m is within manageable limits" in f.lower() for f in assessment.factors)


def test_simulate_moderate_risk_marginal_conditions():
    """Simulate moderate offshore chop & current (e.g. Mumbai High)."""
    assessment = calculate_risk(
        wave_height_m=1.8,
        wind_speed_kmh=28.0,
        wave_period_s=4.9,
        swell_height_m=1.4,
        surface_current_ms=0.72,
        imd_warning_level="Yellow",
        target_time="14:00",
    )
    assert assessment.risk_level == "MODERATE"
    assert 35 <= assessment.risk_score < 60
    assert "advises caution" in assessment.recommendation.lower()
    assert any("moderate wave height" in f.lower() for f in assessment.factors)
    assert any("short wave period" in f.lower() for f in assessment.factors)


def test_simulate_high_risk_squall_conditions():
    """Simulate elevated breaking seas and squally wind (e.g. Mangaluru 06:00)."""
    assessment = calculate_risk(
        wave_height_m=2.4,
        wind_speed_kmh=32.5,
        wave_period_s=8.0,
        swell_height_m=1.9,
        surface_current_ms=0.45,
        imd_warning_level="Yellow",
        target_time="06:00",
    )
    assert assessment.risk_level in ("HIGH", "EXTREME")
    assert assessment.risk_score >= 60
    assert "postponing departure" in assessment.recommendation.lower()
    assert any("high wave height 2.4m" in f.lower() for f in assessment.factors)
    assert any("elevated swell" in f.lower() for f in assessment.factors)


def test_simulate_extreme_risk_cyclone_alert():
    """Simulate severe tropical cyclonic storm (e.g. Paradip)."""
    assessment = calculate_risk(
        wave_height_m=3.8,
        wind_speed_kmh=58.0,
        cyclone_alerts=[{"name": "Tropical Cyclone"}],
        imd_warning_level="Red",
        target_time="08:00",
    )
    assert assessment.risk_level == "EXTREME"
    assert assessment.risk_score >= 80
    assert "strictly recommends postponing departure" in assessment.recommendation.lower()
    assert any("extreme wave height 3.8m" in f.lower() for f in assessment.factors)
    assert any("gale-force wind" in f.lower() for f in assessment.factors)
    assert any("cyclone" in f.lower() for f in assessment.factors)
