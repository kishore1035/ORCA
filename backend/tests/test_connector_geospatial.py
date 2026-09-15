import httpx
import respx
from app.connectors import geospatial


@respx.mock
async def test_geocode_live_success():
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(
            200,
            json=[{"lat": "9.9816", "lon": "76.2999", "display_name": "Kochi Port, Kerala, India"}],
        )
    )
    result = await geospatial.geocode("Kochi port")
    assert result.is_cached is False
    assert result.data["lat"] == 9.9816


@respx.mock
async def test_geocode_falls_back_on_failure():
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        side_effect=httpx.ConnectError("boom")
    )
    result = await geospatial.geocode("Kochi port")
    assert result.is_cached is True
    assert result.data["display_name"] == "Kochi, Kerala, India"


def test_nearest_boundary_distance_reports_inside_polygon_as_zero(monkeypatch, tmp_path):
    geojson_path = tmp_path / "mpa.geojson"
    geojson_path.write_text(
        '{"type": "FeatureCollection", "features": [{"type": "Feature", '
        '"properties": {"name": "Test MPA"}, "geometry": {"type": "Polygon", '
        '"coordinates": [[[75.8, 9.6], [75.9, 9.6], [75.9, 9.7], [75.8, 9.7], [75.8, 9.6]]]}}]}'
    )
    monkeypatch.setattr(geospatial, "MPA_BOUNDARIES_PATH", geojson_path)
    result = geospatial.nearest_boundary_distance_km(9.65, 75.85)
    assert result["nearest_boundary"] == "Test MPA"
    assert result["distance_km"] == 0.0


def test_nearest_boundary_distance_reports_positive_distance_outside_polygon(monkeypatch, tmp_path):
    geojson_path = tmp_path / "mpa.geojson"
    geojson_path.write_text(
        '{"type": "FeatureCollection", "features": [{"type": "Feature", '
        '"properties": {"name": "Test MPA"}, "geometry": {"type": "Polygon", '
        '"coordinates": [[[75.8, 9.6], [75.9, 9.6], [75.9, 9.7], [75.8, 9.7], [75.8, 9.6]]]}}]}'
    )
    monkeypatch.setattr(geospatial, "MPA_BOUNDARIES_PATH", geojson_path)
    result = geospatial.nearest_boundary_distance_km(9.65, 74.0)
    assert result["nearest_boundary"] == "Test MPA"
    assert result["distance_km"] > 0
