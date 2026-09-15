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


@respx.mock
async def test_get_nearby_boundary_live_picks_nearest_named_feature():
    respx.post("https://overpass-api.de/api/interpreter").mock(
        return_value=httpx.Response(
            200,
            json={
                "elements": [
                    {
                        "type": "way", "id": 1,
                        "center": {"lat": 10.76, "lon": 76.66},
                        "tags": {"boundary": "protected_area", "name": "Far Sanctuary"},
                    },
                    {
                        "type": "way", "id": 2,
                        "center": {"lat": 9.9903, "lon": 76.2753},
                        "tags": {"boundary": "protected_area", "name": "Near Sanctuary"},
                    },
                    {
                        # Unnamed feature, closer than the named one -- should be skipped
                        # in favor of a named result the user can actually act on.
                        "type": "way", "id": 3,
                        "center": {"lat": 9.968, "lon": 76.245},
                        "tags": {"boundary": "protected_area"},
                    },
                ]
            },
        )
    )
    result = await geospatial.get_nearby_boundary(9.9679, 76.2444)
    assert result.is_cached is False
    assert result.data["nearest_boundary"] == "Near Sanctuary"
    assert result.data["distance_km"] > 0


@respx.mock
async def test_get_nearby_boundary_returns_none_when_nothing_in_radius():
    respx.post("https://overpass-api.de/api/interpreter").mock(
        return_value=httpx.Response(200, json={"elements": []})
    )
    result = await geospatial.get_nearby_boundary(0.0, 0.0)
    assert result.is_cached is False
    assert result.data["nearest_boundary"] is None
    assert result.data["distance_km"] is None


@respx.mock
async def test_get_nearby_boundary_falls_back_on_failure():
    respx.post("https://overpass-api.de/api/interpreter").mock(side_effect=httpx.ConnectError("boom"))
    result = await geospatial.get_nearby_boundary(9.9679, 76.2444)
    assert result.is_cached is True
    assert result.data["nearest_boundary"] is not None
