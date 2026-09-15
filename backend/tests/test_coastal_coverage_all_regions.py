# backend/tests/test_coastal_coverage_all_regions.py
"""Multi-Region Coastal Coverage Test Suite.

Verifies that the location-first coordinate-based pipeline works generically
across all 9 Indian coastal states and 2 island territories without any
hard-coded city logic.
"""
import pytest
from unittest.mock import AsyncMock
import respx
import httpx

from app.connectors import alerts
from app.connectors.geospatial import compute_coastal_distance, reverse_geocode
from app.connectors.incois import get_marine_forecast, resolve_incois_grid_point
from app.agents.what_if_agent import run_what_if_agent, calculate_destination_coords
from app.graph import build_graph
from app import graph as graph_module


def _mock_connectors(monkeypatch):
    monkeypatch.setattr(alerts, "_listen_for_strikes", lambda prefixes, listen_seconds: [])
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(
            200, json=[{"lat": "12.9141", "lon": "74.8560", "display_name": "Mangaluru, Karnataka, India"}]
        )
    )
    respx.get("https://marine-api.open-meteo.com/v1/marine").mock(
        return_value=httpx.Response(200, json={"hourly": {"wave_height": [1.3], "swell_wave_height": [0.7]}})
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(
            200, json={"hourly": {"wind_speed_10m": [19.0], "wind_direction_10m": [230], "time": ["2026-09-16T06:00"]}}
        )
    )
    respx.get(url__regex=r"jplMURSST41\.json").mock(
        return_value=httpx.Response(200, json={"table": {"rows": [["t", 12.9141, 74.8560, 28.5]]}})
    )
    respx.get(url__regex=r"erdMH1chla1day\.json").mock(
        return_value=httpx.Response(200, json={"table": {"rows": [["t", 12.9141, 74.8560, 0.38]]}})
    )
    respx.get(url__regex=r"gdacs\.org/gdacsapi/api/events/geteventlist/SEARCH").mock(
        return_value=httpx.Response(200, json={"features": []})
    )


COASTAL_TEST_REGIONS = [
    # West Coast
    ("Mangaluru, Karnataka", 12.9141, 74.8560, "Karnataka"),
    ("Munambam / Kochi, Kerala", 10.1800, 76.1700, "Kerala"),
    ("Mumbai / Versova, Maharashtra", 19.1300, 72.8100, "Maharashtra"),
    ("Panaji, Goa", 15.4200, 73.8000, "Goa"),
    ("Kandla / Gulf of Kutch, Gujarat", 23.0000, 70.2200, "Gujarat"),
    # East Coast
    ("Chennai / Kasimedu, Tamil Nadu", 13.1200, 80.3000, "Tamil Nadu"),
    ("Visakhapatnam, Andhra Pradesh", 17.6800, 83.2200, "Andhra Pradesh"),
    ("Puri, Odisha", 19.8000, 85.8300, "Odisha"),
    ("Digha, West Bengal", 21.6300, 87.5100, "West Bengal"),
    # Islands
    ("Port Blair, Andaman & Nicobar", 11.6200, 92.7300, "Andaman & Nicobar"),
    ("Kavaratti, Lakshadweep", 10.5700, 72.6400, "Lakshadweep"),
]


@pytest.mark.parametrize("region_name,lat,lon,expected_sector", COASTAL_TEST_REGIONS)
@pytest.mark.asyncio
async def test_generic_marine_forecast_all_regions(region_name, lat, lon, expected_sector):
    """Verifies that get_marine_forecast resolves any Indian coastal coordinate."""
    res = await get_marine_forecast(lat, lon)
    assert res.source == "INCOIS"
    assert res.data["in_marine_coverage"] is True
    assert res.data["sector"] == expected_sector

    # Check grid resolution & reported distance
    assert "grid_point" in res.data
    assert "grid_distance_km" in res.data
    grid_lat, grid_lon, dist_km = resolve_incois_grid_point(lat, lon)
    assert res.data["grid_point"]["latitude"] == grid_lat
    assert res.data["grid_point"]["longitude"] == grid_lon
    assert res.data["grid_distance_km"] == dist_km
    # Grid resolution is ~0.05 deg, so distance to grid should be <= 8 km anywhere in bounds
    assert 0.0 <= dist_km <= 8.0

    # Verify normalized parameters
    params = res.data.get("parameters", [])
    assert len(params) > 0
    for p in params:
        assert p["latitude"] == lat
        assert p["longitude"] == lon
        assert p["grid_latitude"] == grid_lat
        assert p["grid_longitude"] == grid_lon
        assert p["grid_distance_km"] == dist_km


@pytest.mark.asyncio
async def test_offshore_arabian_sea_coverage():
    """An offshore point 25 km in the Arabian Sea is valid marine coverage."""
    # 25 km west of Mangaluru
    lat, lon = 12.9141, 74.6000
    coastal = compute_coastal_distance(lat, lon)
    assert coastal["in_marine_coverage"] is True
    assert coastal["is_offshore"] is True

    res = await get_marine_forecast(lat, lon)
    assert res.data["in_marine_coverage"] is True
    assert res.data["is_offshore"] is True


@pytest.mark.asyncio
async def test_near_coast_inland_village_evaluation():
    """A coastal village 15 km inland is evaluated at nearest coastal sector with explanation."""
    # ~15 km east of Mangaluru (Bantwal / coastal inland)
    lat, lon = 12.9141, 75.0500
    coastal = compute_coastal_distance(lat, lon)
    assert coastal["in_marine_coverage"] is True
    assert coastal["distance_to_coast_km"] > 5.0
    assert "inland" in coastal["coverage_message"].lower()

    res = await get_marine_forecast(lat, lon)
    assert res.data["in_marine_coverage"] is True
    assert "inland" in res.data["coverage_message"].lower()


@pytest.mark.asyncio
async def test_deep_inland_location_returns_clear_coverage_message():
    """Deep inland location (e.g. Nagpur) gracefully reports out-of-coverage."""
    lat, lon = 21.1458, 79.0882  # Nagpur, Maharashtra (inland)
    coastal = compute_coastal_distance(lat, lon)
    assert coastal["in_marine_coverage"] is False
    assert coastal["distance_to_coast_km"] > 300.0

    res = await get_marine_forecast(lat, lon)
    assert res.data["in_marine_coverage"] is False
    assert "inland" in res.data["coverage_message"].lower()
    assert len(res.data["parameters"]) == 0


@pytest.mark.asyncio
async def test_spatial_what_if_relocation():
    """Verifies counterfactual: 'What if I move 15 km south?'"""
    lat, lon = 12.9141, 74.8560
    new_lat, new_lon = calculate_destination_coords(lat, lon, 15.0, "south")
    assert new_lat < lat
    assert new_lon == lon

    what_if, trace = await run_what_if_agent(
        lat, lon, original_time="06:00", is_spatial=True, move_distance_km=15.0, move_direction="south"
    )

    assert what_if["comparison_type"] == "location"
    assert what_if["spatial_delta_km"] == 15.0
    assert len(what_if["differences"]) >= 3
    assert "Coordinates" in [d["parameter"] for d in what_if["differences"]]
    assert "Significant Wave Height" in [d["parameter"] for d in what_if["differences"]]
    assert "south" in what_if["verdict"].lower()


@pytest.mark.asyncio
@respx.mock
async def test_coordinate_input_without_city_name_in_graph(monkeypatch):
    """User provides only coordinates (e.g. from GPS or Map Click) and asks 'Can I fish here tomorrow?'"""
    _mock_connectors(monkeypatch)
    monkeypatch.setattr(
        graph_module, "create_plan",
        AsyncMock(return_value={
            "intent": "check fishing safety at current coordinates",
            "place_name": None,  # No city name in text!
            "target_time": "06:00",
            "agents": ["weather", "risk", "ocean_analytics"],
            "response_language": "English",
        }),
    )
    monkeypatch.setattr(
        graph_module, "synthesize_answer",
        AsyncMock(return_value="Conditions are evaluated at your selected GPS location (10.18°N, 76.17°E)."),
    )

    graph = build_graph(client=object())

    # Direct coordinate location object from GPS
    location = {
        "latitude": 10.1800,
        "longitude": 76.1700,
        "display_name": "Munambam Fishing Harbour",
        "district": "Ernakulam",
        "state": "Kerala",
        "country": "India",
        "source": "GPS",
    }

    state = await graph.ainvoke({
        "message": "Can I fish here tomorrow at 6 AM?",
        "history": [],
        "location": location,
    })

    assert state.get("final_answer") is not None
    assert state["lat"] == 10.1800
    assert state["lon"] == 76.1700
    assert state["canonical_location"]["source"] == "GPS"
    assert state["canonical_location"]["state"] == "Kerala"
    assert "risk_result" in state
    assert len(state["evidence"]) > 0
