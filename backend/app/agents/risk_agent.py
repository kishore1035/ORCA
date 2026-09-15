from app.connectors.alerts import get_alerts
from app.schemas import TraceEntry

WAVE_HEIGHT_UNSAFE_M = 2.5
WIND_SPEED_UNSAFE_KMH = 40.0


def _assess(weather: dict, alerts_data: dict) -> tuple[str, list[str]]:
    reasons: list[str] = []
    unsafe = False

    if weather["wave_height_m"] > WAVE_HEIGHT_UNSAFE_M:
        unsafe = True
        reasons.append(
            f"Wave height {weather['wave_height_m']}m exceeds safe threshold {WAVE_HEIGHT_UNSAFE_M}m"
        )
    if weather["wind_speed_kmh"] > WIND_SPEED_UNSAFE_KMH:
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


async def run_risk_agent(lat: float, lon: float, weather: dict) -> tuple[dict, TraceEntry]:
    alerts_result = await get_alerts(lat, lon)
    verdict, reasons = _assess(weather, alerts_result.data)
    output = {"verdict": verdict, "reasons": reasons}
    trace = TraceEntry(
        agent="risk",
        inputs={"lat": lat, "lon": lon},
        output=output,
        sources=[alerts_result.source],
        fetched_at=alerts_result.fetched_at,
        is_cached=alerts_result.is_cached,
    )
    return output, trace
