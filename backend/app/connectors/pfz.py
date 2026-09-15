"""Real INCOIS Potential Fishing Zone (PFZ) advisory data -- closing the
"no free fisheries/PFZ feed" gap the ocean_analytics_agent's SST/chlorophyll
heuristic was standing in for. `https://incois.gov.in/MarineFisheries/TextData`
is a plain server-rendered HTML page (not a documented API) listing, per named
coastal landing center, the bearing/distance/depth offshore to that center's
current PFZ advisory point -- free, no key, no IP whitelist (unlike IMD's
`api.imd.gov.in`, which requires manual IP whitelisting and was ruled out for
that reason). It does require a Java servlet session: hitting `TextDataHome`
first sets a JSESSIONID cookie that `TextData?secid=...` is keyed to.

INCOIS splits the coast into 14 sectors (`SEC001`-`SEC014`) selected from a
dropdown, not by lat/lon -- there's no documented endpoint that takes
coordinates directly. This resolves a sector by reverse-geocoding the query
point to an Indian state (Nominatim, free, no key, same service already used
for forward geocoding in connectors/geospatial.py) and mapping state name to
sector id. Three states -- Tamil Nadu, Andhra Pradesh, Andaman & Nicobar --
are each split into two INCOIS sectors that don't correspond to any
Nominatim-reportable boundary; SPLIT_STATE_SECTORS approximates the split
with a latitude threshold. This is a real simplification, not exact
administrative geography, same spirit as the route agent's linear
waypoint interpolation.
"""
import math
import re
from pathlib import Path

import httpx

from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots"
PFZ_SNAPSHOT = DATA_DIR / "pfz_advisory.json"

TEXT_DATA_HOME_URL = "https://incois.gov.in/MarineFisheries/TextDataHome"
TEXT_DATA_URL = "https://incois.gov.in/MarineFisheries/TextData"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
EARTH_RADIUS_KM = 6371.0

# Straight from INCOIS's own "Select Sector" dropdown (see TextDataHome).
STATE_SECTORS = {
    "Gujarat": "SEC001",
    "Maharashtra": "SEC002",
    "Goa": "SEC003",
    "Karnataka": "SEC004",
    "Kerala": "SEC005",
    "Odisha": "SEC010",
    "West Bengal": "SEC011",
    "Lakshadweep": "SEC014",
}
# state -> (latitude threshold, sector north of it, sector south of it).
# Approximate -- see module docstring.
SPLIT_STATE_SECTORS = {
    "Tamil Nadu": (11.0, "SEC007", "SEC006"),
    "Puducherry": (11.0, "SEC007", "SEC006"),
    "Andhra Pradesh": (16.0, "SEC009", "SEC008"),
    "Andaman and Nicobar Islands": (10.0, "SEC012", "SEC013"),
}

_ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.S)
_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _parse_dms(raw: str) -> float:
    degrees, minutes, seconds, hemisphere = raw.split()
    value = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
    return -value if hemisphere.upper() in ("S", "W") else value


def _parse_range(raw: str) -> list[float]:
    low, high = raw.split("-")
    return [float(low), float(high)]


def _parse_landing_centers(html: str) -> list[dict]:
    centers = []
    for row in _ROW_RE.findall(html):
        cells = [c.strip() for c in _CELL_RE.findall(row)]
        if len(cells) != 7 or cells[0] == "From the coast of":
            continue
        name, direction, bearing, distance_km, depth_m, lat_dms, lon_dms = cells
        try:
            centers.append(
                {
                    "name": name,
                    "direction": direction,
                    "bearing_deg": float(bearing),
                    "offshore_distance_km_range": _parse_range(distance_km),
                    "depth_m_range": _parse_range(depth_m),
                    "lat": round(_parse_dms(lat_dms), 5),
                    "lon": round(_parse_dms(lon_dms), 5),
                }
            )
        except ValueError:
            continue
    return centers


async def _resolve_sector(lat: float, lon: float, client: httpx.AsyncClient) -> str:
    resp = await client.get(
        NOMINATIM_REVERSE_URL, params={"lat": lat, "lon": lon, "format": "json", "zoom": 5}
    )
    resp.raise_for_status()
    state = resp.json().get("address", {}).get("state")
    if state in STATE_SECTORS:
        return STATE_SECTORS[state]
    if state in SPLIT_STATE_SECTORS:
        threshold, north_secid, south_secid = SPLIT_STATE_SECTORS[state]
        return north_secid if lat >= threshold else south_secid
    raise ValueError(f"No INCOIS PFZ sector for state {state!r} at ({lat}, {lon})")


async def _fetch_pfz_live(lat: float, lon: float) -> dict:
    async with httpx.AsyncClient(
        timeout=15.0, headers={"User-Agent": "orca-marine-platform/0.1"}
    ) as client:
        secid = await _resolve_sector(lat, lon, client)
        # Establishes the JSESSIONID cookie TextData's sector data is keyed to.
        await client.get(TEXT_DATA_HOME_URL, params={"mfid": 1, "request_locale": "en"})
        resp = await client.get(TEXT_DATA_URL, params={"secid": secid})
        resp.raise_for_status()
        centers = _parse_landing_centers(resp.text)

    if not centers:
        raise ValueError(f"No PFZ landing centers parsed for sector {secid}")

    nearest = min(centers, key=lambda c: _haversine_km(lat, lon, c["lat"], c["lon"]))
    return {
        "sector": secid,
        "nearest_landing_center": nearest["name"],
        "distance_from_query_km": round(_haversine_km(lat, lon, nearest["lat"], nearest["lon"]), 1),
        "direction": nearest["direction"],
        "bearing_deg": nearest["bearing_deg"],
        "offshore_distance_km_range": nearest["offshore_distance_km_range"],
        "depth_m_range": nearest["depth_m_range"],
        "pfz_lat": nearest["lat"],
        "pfz_lon": nearest["lon"],
    }


async def get_pfz_advisory(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback(
        source="incois-pfz-advisory",
        live_fetch=lambda: _fetch_pfz_live(lat, lon),
        snapshot_path=PFZ_SNAPSHOT,
    )
