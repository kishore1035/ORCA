from datetime import date
from pathlib import Path
import httpx
from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots"
SST_SNAPSHOT = DATA_DIR / "sst.json"
CHLOROPHYLL_SNAPSHOT = DATA_DIR / "chlorophyll.json"
ERDDAP_BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"


async def _fetch_sst(lat: float, lon: float) -> dict:
    today = date.today().isoformat()
    url = f"{ERDDAP_BASE}/jplMURSST41.json"
    params = {"analysed_sst": f"[({today}T09:00:00Z)][({lat})][({lon})]"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        payload = resp.json()
    return {"sst_celsius": payload["table"]["rows"][0][-1]}


async def _fetch_chlorophyll(lat: float, lon: float) -> dict:
    today = date.today().isoformat()
    url = f"{ERDDAP_BASE}/erdMH1chla1day.json"
    params = {"chlorophyll": f"[({today}T00:00:00Z)][({lat})][({lon})]"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        payload = resp.json()
    return {"chlorophyll_mg_m3": payload["table"]["rows"][0][-1]}


async def get_sst(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback("noaa-erddap-sst", lambda: _fetch_sst(lat, lon), SST_SNAPSHOT)


async def get_chlorophyll(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback(
        "noaa-erddap-chlorophyll", lambda: _fetch_chlorophyll(lat, lon), CHLOROPHYLL_SNAPSHOT
    )
