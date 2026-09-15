# backend/app/connectors/mosdac.py
"""ISRO / MOSDAC / NRSC connector for satellite bio-optical ocean data.

Provides Oceansat-3 (EOS-06) Ocean Colour Monitor (OCM-3) bio-optical metrics
(chlorophyll, Kd490, TSM) to inform PFZ/advisory-aware fishing analysis.
This connector is optional and non-blocking.
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
    / "mosdac_ocm3.json"
)

MOSDAC_BASE_URL = "https://mosdac.gov.in"


def _extract_mosdac_parameters(
    data: dict, lat: float, lon: float, source: str, data_status: str
) -> list[dict[str, Any]]:
    """Convert MOSDAC satellite metrics into normalized MarineParameter list."""
    ts = data.get("valid_from", datetime.now(timezone.utc).isoformat())
    valid_from = data.get("valid_from")
    valid_until = data.get("valid_until")

    params: list[dict[str, Any]] = []

    if "chlorophyll_mg_m3" in data:
        params.append(
            MarineParameter(
                parameter="chlorophyll",
                value=float(data["chlorophyll_mg_m3"]),
                unit="mg/m³",
                latitude=lat,
                longitude=lon,
                timestamp=ts,
                valid_from=valid_from,
                valid_until=valid_until,
                source=source,
                data_status=data_status,  # type: ignore
                confidence=0.88 if data_status == "LIVE" else 0.82,
            ).model_dump()
        )

    if "kd_490_per_meter" in data:
        params.append(
            MarineParameter(
                parameter="diffuse_attenuation_kd490",
                value=float(data["kd_490_per_meter"]),
                unit="1/m",
                latitude=lat,
                longitude=lon,
                timestamp=ts,
                valid_from=valid_from,
                valid_until=valid_until,
                source=source,
                data_status=data_status,  # type: ignore
                confidence=0.85,
            ).model_dump()
        )

    if "total_suspended_matter_g_m3" in data:
        params.append(
            MarineParameter(
                parameter="total_suspended_matter",
                value=float(data["total_suspended_matter_g_m3"]),
                unit="g/m³",
                latitude=lat,
                longitude=lon,
                timestamp=ts,
                valid_from=valid_from,
                valid_until=valid_until,
                source=source,
                data_status=data_status,  # type: ignore
                confidence=0.85,
            ).model_dump()
        )

    if "sst_celsius" in data:
        params.append(
            MarineParameter(
                parameter="satellite_sst",
                value=float(data["sst_celsius"]),
                unit="°C",
                latitude=lat,
                longitude=lon,
                timestamp=ts,
                valid_from=valid_from,
                valid_until=valid_until,
                source=source,
                data_status=data_status,  # type: ignore
                confidence=0.86,
            ).model_dump()
        )

    return params


async def _live_fetch_mosdac(lat: float, lon: float) -> dict:
    """Attempts live fetch from MOSDAC API if token is provided; otherwise raises to trigger fallback."""
    settings = get_settings()
    token = getattr(settings, "mosdac_token", "")
    if not token:
        raise ValueError("No MOSDAC token configured; non-blocking fallback to verified snapshot")

    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
        resp = await client.get(
            f"{MOSDAC_BASE_URL}/api/v1/ocm3",
            headers=headers,
            params={"lat": lat, "lon": lon},
        )
        resp.raise_for_status()
        return resp.json()


async def get_mosdac_satellite_data(lat: float, lon: float) -> ConnectorResult:
    """Fetch MOSDAC/ISRO satellite data with non-blocking verified fallback."""
    raw_result = await fetch_with_fallback(
        source="ISRO-MOSDAC",
        live_fetch=lambda: _live_fetch_mosdac(lat, lon),
        snapshot_path=SNAPSHOT_PATH,
        live_data_status="LIVE",
    )

    data_status = raw_result.data_status
    params = _extract_mosdac_parameters(
        raw_result.data, lat, lon, source="ISRO-MOSDAC", data_status=data_status
    )

    enriched_data = {
        **raw_result.data,
        "parameters": params,
    }

    return ConnectorResult(
        data=enriched_data,
        source="ISRO-MOSDAC",
        fetched_at=raw_result.fetched_at,
        is_cached=raw_result.is_cached,
        data_status=data_status,
    )
