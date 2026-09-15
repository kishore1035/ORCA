from app.connectors.ocean_analytics import get_sst, get_chlorophyll, get_sst_trend
from app.schemas import TraceEntry

# Simplified, explicitly-labeled heuristic (not an official PFZ advisory algorithm):
# a warm-water front (27-30C) combined with elevated chlorophyll (>=0.2 mg/m3)
# indicates a likely nutrient-rich front favorable for fish aggregation.
SST_MIN_C = 27.0
SST_MAX_C = 30.0
CHLOROPHYLL_MIN_MG_M3 = 0.2

# Below this absolute change (degrees C) across the trend window, call it "stable"
# rather than over-interpreting normal day-to-day noise as a real trend.
TREND_STABLE_THRESHOLD_C = 0.3


def _trend_direction(trend: list[dict]) -> str:
    if not trend:
        return "unknown"
    delta = trend[-1]["sst_celsius"] - trend[0]["sst_celsius"]
    if abs(delta) < TREND_STABLE_THRESHOLD_C:
        return "stable"
    return "warming" if delta > 0 else "cooling"


def _productivity_trend(trend: list[dict]) -> tuple[str, str]:
    """Deterministic 'why has it changed' signal for the reporting agent,
    built from real SST trend data (not fabricated fish-catch statistics --
    no free fish-productivity dataset exists). Compares whether SST was
    inside the favorable PFZ band at the start vs. the end of the trend
    window; chlorophyll trend data isn't available so this covers only the
    SST half of the PFZ score."""
    if not trend:
        return "unknown", "No SST trend data available to assess a change."
    start_c, end_c = trend[0]["sst_celsius"], trend[-1]["sst_celsius"]
    start_ok = SST_MIN_C <= start_c <= SST_MAX_C
    end_ok = SST_MIN_C <= end_c <= SST_MAX_C
    note = (
        f"SST moved from {start_c}°C ({'within' if start_ok else 'outside'} the "
        f"{SST_MIN_C}-{SST_MAX_C}°C favorable band) to {end_c}°C "
        f"({'within' if end_ok else 'outside'} it) over the observed period."
    )
    if end_ok and not start_ok:
        return "improving", note
    if start_ok and not end_ok:
        return "declining", note
    return "stable", note


def _score(sst_c: float, chlorophyll: float) -> tuple[str, list[str]]:
    sst_ok = SST_MIN_C <= sst_c <= SST_MAX_C
    chl_ok = chlorophyll >= CHLOROPHYLL_MIN_MG_M3
    reasons = [
        f"SST {sst_c}°C {'within' if sst_ok else 'outside'} favorable range "
        f"{SST_MIN_C}-{SST_MAX_C}°C",
        f"Chlorophyll {chlorophyll} mg/m³ {'meets' if chl_ok else 'is below'} "
        f"threshold {CHLOROPHYLL_MIN_MG_M3} mg/m³",
    ]
    if sst_ok and chl_ok:
        return "high", reasons
    if sst_ok or chl_ok:
        return "moderate", reasons
    return "low", reasons


async def run_ocean_analytics_agent(lat: float, lon: float) -> tuple[dict, TraceEntry]:
    sst_result = await get_sst(lat, lon)
    chl_result = await get_chlorophyll(lat, lon)
    trend_result = await get_sst_trend(lat, lon)
    sst_c = sst_result.data["sst_celsius"]
    chlorophyll = chl_result.data["chlorophyll_mg_m3"]
    trend = trend_result.data["sst_trend"]
    likelihood, reasons = _score(sst_c, chlorophyll)
    productivity_trend, productivity_note = _productivity_trend(trend)
    output = {
        "sst_celsius": sst_c,
        "chlorophyll_mg_m3": chlorophyll,
        "pfz_likelihood": likelihood,
        "reasons": reasons,
        "sst_trend_celsius": trend,
        "sst_trend_direction": _trend_direction(trend),
        "productivity_trend": productivity_trend,
        "productivity_note": productivity_note,
    }
    trace = TraceEntry(
        agent="ocean_analytics",
        inputs={"lat": lat, "lon": lon},
        output=output,
        sources=[sst_result.source, chl_result.source, trend_result.source],
        fetched_at=max(sst_result.fetched_at, chl_result.fetched_at, trend_result.fetched_at),
        is_cached=sst_result.is_cached or chl_result.is_cached or trend_result.is_cached,
    )
    return output, trace
