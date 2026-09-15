from app.agents.risk_engine import calculate_risk
from app.schemas import RiskAssessment


def test_calculate_risk_low_calm_conditions():
    res = calculate_risk(
        wave_height_m=0.8,
        wind_speed_kmh=12.0,
        wave_period_s=7.5,
        swell_height_m=0.5,
        surface_current_ms=0.2,
        imd_warning_level="Green",
        target_time="06:00",
    )
    assert isinstance(res, RiskAssessment)
    assert res.risk_level == "LOW"
    assert res.risk_score < 30
    assert "approves departure" in res.recommendation.lower()


def test_calculate_risk_high_elevated_waves_and_wind():
    res = calculate_risk(
        wave_height_m=2.3,
        wind_speed_kmh=28.5,
        wave_period_s=7.8,
        swell_height_m=1.9,
        surface_current_ms=0.45,
        imd_warning_level="Yellow",
        target_time="06:00",
    )
    assert isinstance(res, RiskAssessment)
    assert res.risk_level in ("HIGH", "EXTREME")
    assert res.risk_score >= 60
    assert "postponing departure" in res.recommendation.lower()
    assert any("wave height 2.3m" in f.lower() for f in res.factors)


def test_calculate_risk_extreme_cyclone_alert():
    res = calculate_risk(
        wave_height_m=3.5,
        wind_speed_kmh=55.0,
        cyclone_alerts=[{"name": "Tropical Cyclone"}],
        target_time="12:00",
    )
    assert res.risk_level == "EXTREME"
    assert res.risk_score >= 80
    assert any("cyclone" in f.lower() for f in res.factors)


def test_calculate_risk_moderate_calmer_window():
    res = calculate_risk(
        wave_height_m=1.4,
        wind_speed_kmh=16.2,
        wave_period_s=6.5,
        swell_height_m=1.1,
        surface_current_ms=0.28,
        target_time="11:00",
    )
    assert res.risk_level == "MODERATE" or res.risk_score < 60
    assert res.risk_score < 50
