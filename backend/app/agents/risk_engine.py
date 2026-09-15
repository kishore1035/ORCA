# backend/app/agents/risk_engine.py
"""Deterministic, explainable marine risk calculation engine.

NOTE: All thresholds and weights are prototype decision-policy heuristics
designed for coastal and artisanal fishing safety evaluation, NOT statutory
or official INCOIS/IMD safety standards.
"""
from typing import Any
from app.schemas import RiskAssessment

# Decision-policy heuristic thresholds
WAVE_MODERATE_M = 1.5
WAVE_HIGH_M = 2.0
WAVE_EXTREME_M = 2.8

WIND_MODERATE_KMH = 25.0
WIND_HIGH_KMH = 38.0
WIND_EXTREME_KMH = 50.0

CURRENT_MODERATE_MS = 0.6
CURRENT_HIGH_MS = 1.0


def calculate_risk(
    wave_height_m: float,
    wind_speed_kmh: float,
    wave_period_s: float | None = None,
    swell_height_m: float | None = None,
    surface_current_ms: float | None = None,
    imd_warning_level: str | None = None,
    cyclone_alerts: list[dict] | None = None,
    lightning_alerts: list[dict] | None = None,
    within_warning_zone: bool = False,
    boundary_name: str | None = None,
    target_time: str | None = None,
) -> RiskAssessment:
    """Computes transparent, explainable marine risk score (0-100)."""
    score = 0.0
    factors: list[str] = []

    # 1. Wave Height Hazard (up to 40 points)
    if wave_height_m > WAVE_EXTREME_M:
        score += 40.0
        factors.append(
            f"Extreme wave height {wave_height_m:.1f}m exceeds severe threshold {WAVE_EXTREME_M}m (+40)"
        )
    elif wave_height_m > WAVE_HIGH_M:
        score += 30.0
        factors.append(
            f"High wave height {wave_height_m:.1f}m exceeds cautionary limit {WAVE_HIGH_M}m (+30)"
        )
    elif wave_height_m > WAVE_MODERATE_M:
        score += 18.0
        factors.append(
            f"Moderate wave height {wave_height_m:.1f}m above baseline {WAVE_MODERATE_M}m (+18)"
        )
    else:
        score += max(0.0, wave_height_m * 6.0)
        factors.append(f"Wave height {wave_height_m:.1f}m is within manageable limits")

    # 2. Swell & Period penalty (up to 15 points)
    if swell_height_m and swell_height_m > 1.6:
        score += 10.0
        factors.append(f"Elevated swell height {swell_height_m:.1f}m creates rough coastal break (+10)")
    if wave_period_s and wave_period_s < 5.5 and wave_height_m > 1.5:
        score += 5.0
        factors.append(f"Short wave period {wave_period_s:.1f}s indicates steep, choppy seas (+5)")

    # 3. Wind Speed Hazard (up to 30 points)
    if wind_speed_kmh > WIND_EXTREME_KMH:
        score += 30.0
        factors.append(f"Gale-force wind speed {wind_speed_kmh:.1f} km/h (+30)")
    elif wind_speed_kmh > WIND_HIGH_KMH:
        score += 22.0
        factors.append(f"Strong coastal wind {wind_speed_kmh:.1f} km/h exceeds safe threshold {WIND_HIGH_KMH} km/h (+22)")
    elif wind_speed_kmh > WIND_MODERATE_KMH:
        score += 12.0
        factors.append(f"Moderate wind {wind_speed_kmh:.1f} km/h above threshold {WIND_MODERATE_KMH} km/h (+12)")
    else:
        score += max(0.0, wind_speed_kmh * 0.25)
        factors.append(f"Wind speed {wind_speed_kmh:.1f} km/h is favorable")

    # 4. Surface Currents (up to 10 points)
    if surface_current_ms and surface_current_ms > CURRENT_HIGH_MS:
        score += 10.0
        factors.append(f"Strong surface current velocity {surface_current_ms:.2f} m/s (+10)")
    elif surface_current_ms and surface_current_ms > CURRENT_MODERATE_MS:
        score += 5.0
        factors.append(f"Moderate surface drift {surface_current_ms:.2f} m/s (+5)")

    # 5. IMD Severe Weather Warning (up to 30 points)
    if imd_warning_level:
        lvl = imd_warning_level.strip().lower()
        if "red" in lvl:
            score += 30.0
            factors.append("Active IMD Red Warning (Severe Weather Alert) (+30)")
        elif "orange" in lvl:
            score += 20.0
            factors.append("Active IMD Orange Warning (Alert - Be Prepared) (+20)")
        elif "yellow" in lvl:
            score += 10.0
            factors.append("Active IMD Yellow Warning (Watch - Squally Weather Advisory) (+10)")

    # 6. Cyclone & Lightning Alerts
    if cyclone_alerts:
        score += 35.0
        names = ", ".join(a.get("name", "Unnamed") for a in cyclone_alerts)
        factors.append(f"Active Tropical Cyclone Advisory ({names}) (+35)")

    if lightning_alerts:
        score += 15.0
        factors.append("Active lightning strikes recorded within coastal radius (+15)")

    # 7. Boundary / MPA Geofence
    if within_warning_zone and boundary_name:
        score += 5.0
        factors.append(f"Near marine protected boundary: {boundary_name} (+5)")

    # Clamp score to [0, 100]
    final_score = int(min(100, max(0, round(score))))

    # Risk level classification
    if final_score >= 80:
        level = "EXTREME"
        recom = (
            f"ORCA strictly recommends postponing departure"
            + (f" at {target_time}" if target_time else "")
            + ". Dangerous sea state and active meteorological advisories."
        )
    elif final_score >= 60:
        level = "HIGH"
        recom = (
            f"ORCA recommends postponing departure"
            + (f" at {target_time}" if target_time else "")
            + ". Elevated wave height and strong winds present hazardous conditions for small craft."
        )
    elif final_score >= 35:
        level = "MODERATE"
        recom = (
            f"ORCA advises caution"
            + (f" at {target_time}" if target_time else "")
            + ". Borderline conditions; mechanized vessels may operate with vigilance, but small crafts should stay near shore."
        )
    else:
        level = "LOW"
        recom = (
            f"ORCA approves departure"
            + (f" at {target_time}" if target_time else "")
            + ". Marine and weather conditions are calm and favorable."
        )

    return RiskAssessment(
        risk_score=final_score,
        risk_level=level,  # type: ignore
        factors=factors,
        recommendation=recom,
        confidence=0.91,
    )
