from datetime import date, timedelta
from pathlib import Path
import httpx
from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots"
SST_SNAPSHOT = DATA_DIR / "sst.json"
CHLOROPHYLL_SNAPSHOT = DATA_DIR / "chlorophyll.json"
ERDDAP_BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"

# MUR SST / chlorophyll products lag ~1 day behind the current date, so
# requesting `date.today()` reliably 404s (past the dataset's time axis
# maximum). Stay two days behind to be safe.
ERDDAP_DATA_LAG_DAYS = 2


async def _fetch_sst(lat: float, lon: float) -> dict:
    target_date = (date.today() - timedelta(days=ERDDAP_DATA_LAG_DAYS)).isoformat()
    # ERDDAP's griddap subset syntax requires the bracket expression appended
    # directly to the variable name with no "=" -- httpx's dict-based params=
    # encoding would insert one (e.g. "?analysed_sst=%5B..."), which ERDDAP
    # rejects. Build the query string manually instead.
    url = f"{ERDDAP_BASE}/jplMURSST41.json?analysed_sst[({target_date}T09:00:00Z)][({lat})][({lon})]"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        payload = resp.json()
    return {"sst_celsius": payload["table"]["rows"][0][-1]}


async def _fetch_chlorophyll(lat: float, lon: float) -> dict:
    target_date = (date.today() - timedelta(days=ERDDAP_DATA_LAG_DAYS)).isoformat()
    url = f"{ERDDAP_BASE}/erdMH1chla1day.json?chlorophyll[({target_date}T00:00:00Z)][({lat})][({lon})]"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        payload = resp.json()
    return {"chlorophyll_mg_m3": payload["table"]["rows"][0][-1]}


async def get_sst(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback("noaa-erddap-sst", lambda: _fetch_sst(lat, lon), SST_SNAPSHOT)


async def get_chlorophyll(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback(
        "noaa-erddap-chlorophyll", lambda: _fetch_chlorophyll(lat, lon), CHLOROPHYLL_SNAPSHOT
    )
