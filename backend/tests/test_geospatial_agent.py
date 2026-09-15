from datetime import datetime, timezone
from app.agents import geospatial_agent
from app.schemas import ConnectorResult


def _geo_result(**overrides):
    defaults = dict(
        data={"lat": 9.93, "lon": 76.27, "display_name": "Kochi, Kerala, India"},
        source="nominatim",
        fetched_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        is_cached=False,
    )
    defaults.update(overrides)
    return ConnectorResult(**defaults)


def _boundary_result(**overrides):
    defaults = dict(
        data={"nearest_boundary": "Example MPA", "distance_km": 12.0},
        source="overpass-osm-protected-areas",
        fetched_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        is_cached=False,
    )
    defaults.update(overrides)
    return ConnectorResult(**defaults)


async def test_run_geospatial_agent_returns_output_and_trace(monkeypatch):
    geo_result = _geo_result()
    boundary_result = _boundary_result()

    async def fake_geocode(place_name):
        return geo_result

    async def fake_get_nearby_boundary(lat, lon):
        return boundary_result

    monkeypatch.setattr(geospatial_agent, "geocode", fake_geocode)
    monkeypatch.setattr(geospatial_agent, "get_nearby_boundary", fake_get_nearby_boundary)

    output, trace = await geospatial_agent.run_geospatial_agent("Kochi")

    assert output["lat"] == 9.93
    assert output["within_warning_zone"] is False
    assert trace.agent == "geospatial"
    assert trace.sources == ["nominatim", "overpass-osm-protected-areas"]


async def test_run_geospatial_agent_flags_warning_zone(monkeypatch):
    geo_result = _geo_result(data={"lat": 9.65, "lon": 75.85, "display_name": "Near MPA"})
    boundary_result = _boundary_result(data={"nearest_boundary": "Example MPA", "distance_km": 2.0})

    async def fake_geocode(place_name):
        return geo_result

    async def fake_get_nearby_boundary(lat, lon):
        return boundary_result

    monkeypatch.setattr(geospatial_agent, "geocode", fake_geocode)
    monkeypatch.setattr(geospatial_agent, "get_nearby_boundary", fake_get_nearby_boundary)

    output, _ = await geospatial_agent.run_geospatial_agent("Near MPA")
    assert output["within_warning_zone"] is True
    assert output["geofence_warning"] == (
        "Within 2.0km of Example MPA -- check local marine protected area / boundary "
        "regulations before entering."
    )


async def test_run_geospatial_agent_omits_geofence_warning_outside_zone(monkeypatch):
    geo_result = _geo_result()
    boundary_result = _boundary_result(data={"nearest_boundary": "Example MPA", "distance_km": 48.4})

    async def fake_geocode(place_name):
        return geo_result

    async def fake_get_nearby_boundary(lat, lon):
        return boundary_result

    monkeypatch.setattr(geospatial_agent, "geocode", fake_geocode)
    monkeypatch.setattr(geospatial_agent, "get_nearby_boundary", fake_get_nearby_boundary)

    output, _ = await geospatial_agent.run_geospatial_agent("Kochi")
    assert "geofence_warning" not in output


async def test_run_geospatial_agent_handles_no_boundary_found(monkeypatch):
    geo_result = _geo_result()
    boundary_result = _boundary_result(data={"nearest_boundary": None, "distance_km": None})

    async def fake_geocode(place_name):
        return geo_result

    async def fake_get_nearby_boundary(lat, lon):
        return boundary_result

    monkeypatch.setattr(geospatial_agent, "geocode", fake_geocode)
    monkeypatch.setattr(geospatial_agent, "get_nearby_boundary", fake_get_nearby_boundary)

    output, _ = await geospatial_agent.run_geospatial_agent("Kochi")
    assert output["within_warning_zone"] is False
    assert "geofence_warning" not in output


async def test_run_geospatial_agent_flags_location_fallback_when_cached(monkeypatch):
    geo_result = _geo_result(is_cached=True)
    boundary_result = _boundary_result()

    async def fake_geocode(place_name):
        return geo_result

    async def fake_get_nearby_boundary(lat, lon):
        return boundary_result

    monkeypatch.setattr(geospatial_agent, "geocode", fake_geocode)
    monkeypatch.setattr(geospatial_agent, "get_nearby_boundary", fake_get_nearby_boundary)

    output, trace = await geospatial_agent.run_geospatial_agent("Some Unresolvable Place")
    assert output["location_fallback"] is True
    # or() semantics: geocode cached alone makes the whole result cached
    assert trace.is_cached is True


async def test_run_geospatial_agent_omits_location_fallback_when_live(monkeypatch):
    geo_result = _geo_result()
    boundary_result = _boundary_result()

    async def fake_geocode(place_name):
        return geo_result

    async def fake_get_nearby_boundary(lat, lon):
        return boundary_result

    monkeypatch.setattr(geospatial_agent, "geocode", fake_geocode)
    monkeypatch.setattr(geospatial_agent, "get_nearby_boundary", fake_get_nearby_boundary)

    output, trace = await geospatial_agent.run_geospatial_agent("Kochi")
    assert "location_fallback" not in output
    assert trace.is_cached is False
