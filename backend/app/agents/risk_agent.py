from app.connectors.alerts import get_cyclone_alerts, get_lightning_alerts
from app.connectors.imd import get_imd_warnings
from app.agents.risk_engine import calculate_risk
from app.schemas import TraceEntry

WAVE_HEIGHT_UNSAFE_M = 2.5
WIND_SPEED_UNSAFE_KMH = 40.0


def _assess(weather: dict, alerts_data: dict) -> tuple[str, list[str]]:
    reasons: list[str] = []
    unsafe = False

    if weather.get("wave_height_m", 0.0) > WAVE_HEIGHT_UNSAFE_M:
        unsafe = True
        reasons.append(
            f"Wave height {weather['wave_height_m']}m exceeds safe threshold {WAVE_HEIGHT_UNSAFE_M}m"
        )
    if weather.get("wind_speed_kmh", 0.0) > WIND_SPEED_UNSAFE_KMH:
        unsafe = True
        reasons.append(
            f"Wind speed {weather['wind_speed_kmh']}km/h exceeds safe threshold {WIND_SPEED_UNSAFE_KMH}km/h"
        )
    if alerts_data.get("cyclone_alerts"):
        unsafe = True
        names = ", ".join(a["name"] for a in alerts_data["cyclone_alerts"])
        reasons.append(f"Active cyclone alert(s): {names}")
    if alerts_data.get("lightning_alerts"):
        unsafe = True
        reasons.append("Active lightning alert in the area")

    if not reasons:
        reasons.append("No hazardous conditions found in wave, wind, cyclone, or lightning data")

    return ("unsafe" if unsafe else "safe"), reasons


async def run_risk_agent(
    lat: float, lon: float, weather: dict, geo: dict | None = None
) -> tuple[dict, TraceEntry]:
    cyclone_result = await get_cyclone_alerts(lat, lon)
    lightning_result = await get_lightning_alerts(lat, lon)
    alerts_data = {
        "cyclone_alerts": cyclone_result.data["cyclone_alerts"],
        "lightning_alerts": lightning_result.data["lightning_alerts"],
    }
    verdict, reasons = _assess(weather, alerts_data)

    # Calculate transparent deterministic risk score (0-100)
    risk_assessment = calculate_risk(
        wave_height_m=float(weather.get("wave_height_m", 1.0)),
        wind_speed_kmh=float(weather.get("wind_speed_kmh", 15.0)),
        wave_period_s=float(weather.get("wave_period_s", 7.0)) if weather.get("wave_period_s") else None,
        swell_height_m=float(weather.get("swell_height_m", 0.8)) if weather.get("swell_height_m") else None,
        surface_current_ms=float(weather.get("surface_current_speed_ms", 0.3)) if weather.get("surface_current_speed_ms") else None,
        imd_warning_level=weather.get("warning_level"),
        cyclone_alerts=alerts_data["cyclone_alerts"],
        lightning_alerts=alerts_data["lightning_alerts"],
        within_warning_zone=geo.get("within_warning_zone", False) if geo else False,
        boundary_name=geo.get("nearest_boundary") if geo else None,
        target_time=weather.get("forecast_time"),
    )

    output = {
        "verdict": verdict,
        "reasons": reasons,
        "risk_score": risk_assessment.risk_score,
        "risk_level": risk_assessment.risk_level,
        "factors": risk_assessment.factors,
        "recommendation": risk_assessment.recommendation,
        "confidence": risk_assessment.confidence,
    }

    sources = [cyclone_result.source, lightning_result.source]
    if "IMD" in weather.get("sources", []):
        sources.append("IMD")

    trace = TraceEntry(
        agent="risk",
        inputs={"lat": lat, "lon": lon},
        output=output,
        sources=[cyclone_result.source, lightning_result.source],
        fetched_at=max(cyclone_result.fetched_at, lightning_result.fetched_at),
        is_cached=cyclone_result.is_cached or lightning_result.is_cached,
    )
    return output, trace

