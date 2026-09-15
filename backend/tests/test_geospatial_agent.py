from datetime import datetime, timezone
from app.agents import geospatial_agent
from app.schemas import ConnectorResult


async def test_run_geospatial_agent_returns_output_and_trace(monkeypatch):
    geo_result = ConnectorResult(
        data={"lat": 9.93, "lon": 76.27, "display_name": "Kochi, Kerala, India"},
        source="nominatim",
        fetched_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        is_cached=False,
    )

    async def fake_geocode(place_name):
        return geo_result

    def fake_nearest(lat, lon):
        return {"nearest_boundary": "Example MPA", "distance_km": 12.0, "source": "static-mpa-imbl-snapshot"}

    monkeypatch.setattr(geospatial_agent, "geocode", fake_geocode)
    monkeypatch.setattr(geospatial_agent, "nearest_boundary_distance_km", fake_nearest)

    output, trace = await geospatial_agent.run_geospatial_agent("Kochi")

    assert output["lat"] == 9.93
    assert output["within_warning_zone"] is False
    assert trace.agent == "geospatial"
    assert trace.sources == ["nominatim", "static-mpa-imbl-snapshot"]


async def test_run_geospatial_agent_flags_warning_zone(monkeypatch):
    geo_result = ConnectorResult(
        data={"lat": 9.65, "lon": 75.85, "display_name": "Near MPA"},
        source="nominatim",
        fetched_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        is_cached=False,
    )

    async def fake_geocode(place_name):
        return geo_result

    def fake_nearest(lat, lon):
        return {"nearest_boundary": "Example MPA", "distance_km": 2.0, "source": "static-mpa-imbl-snapshot"}

    monkeypatch.setattr(geospatial_agent, "geocode", fake_geocode)
    monkeypatch.setattr(geospatial_agent, "nearest_boundary_distance_km", fake_nearest)

    output, _ = await geospatial_agent.run_geospatial_agent("Near MPA")
    assert output["within_warning_zone"] is True
