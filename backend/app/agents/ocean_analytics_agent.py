from app.connectors.ocean_analytics import get_sst, get_chlorophyll
from app.schemas import TraceEntry

# Simplified, explicitly-labeled heuristic (not an official PFZ advisory algorithm):
# a warm-water front (27-30C) combined with elevated chlorophyll (>=0.2 mg/m3)
# indicates a likely nutrient-rich front favorable for fish aggregation.
SST_MIN_C = 27.0
SST_MAX_C = 30.0
CHLOROPHYLL_MIN_MG_M3 = 0.2


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
    sst_c = sst_result.data["sst_celsius"]
    chlorophyll = chl_result.data["chlorophyll_mg_m3"]
    likelihood, reasons = _score(sst_c, chlorophyll)
    output = {
        "sst_celsius": sst_c,
        "chlorophyll_mg_m3": chlorophyll,
        "pfz_likelihood": likelihood,
        "reasons": reasons,
    }
    trace = TraceEntry(
        agent="ocean_analytics",
        inputs={"lat": lat, "lon": lon},
        output=output,
        sources=[sst_result.source, chl_result.source],
        fetched_at=max(sst_result.fetched_at, chl_result.fetched_at),
        is_cached=sst_result.is_cached or chl_result.is_cached,
    )
    return output, trace
