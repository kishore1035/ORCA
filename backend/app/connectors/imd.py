# backend/app/connectors/imd.py
"""IMD (India Meteorological Department) connector.

Primary weather, coastal bulletin, and severe warning provider for India.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import httpx

from app.config import get_settings
from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult, MarineParameter

SNAPSHOT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / "snapshots"
    / "imd_mangalore.json"
)

IMD_BASE_URL = "https://api.imd.gov.in"


def _extract_imd_parameters(
    data: dict, lat: float, lon: float, source: str, data_status: str
) -> list[dict[str, Any]]:
    """Convert IMD warning metrics into normalized MarineParameter list."""
    ts = data.get("valid_from", datetime.now(timezone.utc).isoformat())
    valid_from = data.get("valid_from")
    valid_until = data.get("valid_until")

    params: list[dict[str, Any]] = []

    if "warning_level" in data:
        params.append(
            MarineParameter(
                parameter="weather_warning_level",
                value=data["warning_level"],
                unit="",
                latitude=lat,
                longitude=lon,
                timestamp=ts,
                valid_from=valid_from,
                valid_until=valid_until,
                source=source,
                data_status=data_status,  # type: ignore
                confidence=0.95 if data_status == "FORECAST" else 0.88,
            ).model_dump()
        )

    if "rainfall_forecast_mm" in data:
        params.append(
            MarineParameter(
                parameter="rainfall_forecast",
                value=float(data["rainfall_forecast_mm"]),
                unit="mm",
                latitude=lat,
                longitude=lon,
                timestamp=ts,
                valid_from=valid_from,
                valid_until=valid_until,
                source=source,
                data_status=data_status,  # type: ignore
                confidence=0.90 if data_status == "FORECAST" else 0.85,
            ).model_dump()
        )

    if "port_warning_signal" in data:
        params.append(
            MarineParameter(
                parameter="port_warning_signal",
                value=int(data["port_warning_signal"]),
                unit="",
                latitude=lat,
                longitude=lon,
                timestamp=ts,
                valid_from=valid_from,
                valid_until=valid_until,
                source=source,
                data_status=data_status,  # type: ignore
                confidence=0.95 if data_status == "FORECAST" else 0.88,
            ).model_dump()
        )

    return params


async def _live_fetch_imd(lat: float, lon: float) -> dict:
    """Queries official IMD API gateway with configured credentials."""
    settings = get_settings()
    api_key = getattr(settings, "imd_api_key", "")
    if not api_key:
        raise ValueError("No IMD API key configured; triggering verified fallback")

    headers = {
        "X-API-KEY": api_key,
        "Authorization": f"Bearer {api_key}",
    }

    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
        resp = await client.get(f"{IMD_BASE_URL}/api/v1/coastalbulletin", headers=headers)
        resp.raise_for_status()
        bulletin = resp.json()

        resp2 = await client.get(f"{IMD_BASE_URL}/api/v1/districtwarning", headers=headers)
        resp2.raise_for_status()
        warning = resp2.json()

    return {
        "station": "Coastal Station",
        "district": "Coastal District",
        "warning_level": warning.get("warning_level", "Green"),
        "warning_type": warning.get("warning_type", "General Advisory"),
        "coastal_bulletin": bulletin.get("text", "No active squalls observed"),
        "port_warning_signal": bulletin.get("port_signal", 0),
        "rainfall_forecast_mm": warning.get("rainfall_mm", 0.0),
        "cyclone_alerts": warning.get("cyclones", []),
        "valid_from": datetime.now(timezone.utc).isoformat(),
        "valid_until": datetime.now(timezone.utc).isoformat(),
    }


async def get_imd_warnings(lat: float, lon: float) -> ConnectorResult:
    """Fetch IMD weather & marine warnings with verified fallback."""
    raw_result = await fetch_with_fallback(
        source="IMD",
        live_fetch=lambda: _live_fetch_imd(lat, lon),
        snapshot_path=SNAPSHOT_PATH,
        live_data_status="FORECAST",
    )

    data_status = raw_result.data_status
    params = _extract_imd_parameters(
        raw_result.data, lat, lon, source="IMD", data_status=data_status
    )

    enriched_data = {
        **raw_result.data,
        "parameters": params,
    }

    return ConnectorResult(
        data=enriched_data,
        source="IMD",
        fetched_at=raw_result.fetched_at,
        is_cached=raw_result.is_cached,
        data_status=data_status,
    )
