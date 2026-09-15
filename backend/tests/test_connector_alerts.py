import httpx
import respx
from app.connectors import alerts


def test_geohash_encode_known_value():
    # Known reference value: geohash for (57.64911, 10.40744) at precision 6 is "u4pruy".
    assert alerts._geohash_encode(57.64911, 10.40744, 6) == "u4pruy"


def test_tile_prefixes_includes_center_and_is_a_nonempty_set():
    prefixes = alerts._tile_prefixes(9.97, 76.24, radius_km=300, precision=2)
    assert alerts._geohash_encode(9.97, 76.24, 2) in prefixes
    assert len(prefixes) >= 1


async def test_fetch_lightning_live_filters_to_radius(monkeypatch):
    def fake_listen(prefixes, listen_seconds):
        return [
            {"lat": 9.97, "lon": 76.24, "time": 1234},  # ~0km -- inside radius
            {"lat": 30.0, "lon": 76.24, "time": 5678},  # far away -- outside radius
        ]

    monkeypatch.setattr(alerts, "_listen_for_strikes", fake_listen)

    result = await alerts._fetch_lightning_live(9.97, 76.24)

    assert len(result["lightning_alerts"]) == 1
    assert result["lightning_alerts"][0]["lat"] == 9.97


async def test_get_lightning_alerts_live_success(monkeypatch):
    monkeypatch.setattr(
        alerts, "_listen_for_strikes",
        lambda prefixes, listen_seconds: [{"lat": 9.97, "lon": 76.24, "time": 1234}],
    )
    result = await alerts.get_lightning_alerts(9.97, 76.24)
    assert result.is_cached is False
    assert result.source == "blitzortung-mqtt"
    assert len(result.data["lightning_alerts"]) == 1


async def test_get_lightning_alerts_falls_back_on_failure(monkeypatch):
    def fake_listen(prefixes, listen_seconds):
        raise ConnectionError("mqtt broker unreachable")

    monkeypatch.setattr(alerts, "_listen_for_strikes", fake_listen)
    result = await alerts.get_lightning_alerts(9.97, 76.24)
    assert result.is_cached is True
    assert result.source == "blitzortung-mqtt"
    assert result.data["lightning_alerts"] == []


@respx.mock
async def test_get_cyclone_alerts_live_filters_to_nearby_current_cyclones():
    respx.get(url__regex=r"gdacs\.org/gdacsapi/api/events/geteventlist/SEARCH").mock(
        return_value=httpx.Response(
            200,
            json={
                "features": [
                    {
                        "geometry": {"coordinates": [76.5, 10.2]},
                        "properties": {
                            "eventtype": "TC",
                            "name": "Tropical Cyclone NEARBY-26",
                            "alertlevel": "Orange",
                            "iscurrent": "true",
                            "fromdate": "2026-09-15T00:00:00",
                            "todate": "2026-09-16T00:00:00",
                        },
                    },
                    {
                        "geometry": {"coordinates": [148.9, 14.9]},
                        "properties": {
                            "eventtype": "TC",
                            "name": "Tropical Cyclone FAR-26",
                            "alertlevel": "Green",
                            "iscurrent": "true",
                            "fromdate": "2026-09-15T00:00:00",
                            "todate": "2026-09-16T00:00:00",
                        },
                    },
                    {
                        "geometry": {"coordinates": [76.6, 10.3]},
                        "properties": {
                            "eventtype": "FL",
                            "name": "Flood in India",
                            "alertlevel": "Green",
                            "iscurrent": "true",
                            "fromdate": "2026-09-15T00:00:00",
                            "todate": "2026-09-16T00:00:00",
                        },
                    },
                ]
            },
        )
    )
    result = await alerts.get_cyclone_alerts(10.0, 76.0)
    assert result.is_cached is False
    names = [a["name"] for a in result.data["cyclone_alerts"]]
    assert names == ["Tropical Cyclone NEARBY-26"]


@respx.mock
async def test_get_cyclone_alerts_falls_back_on_failure():
    respx.get(url__regex=r"gdacs\.org/gdacsapi/api/events/geteventlist/SEARCH").mock(
        side_effect=httpx.ConnectError("boom")
    )
    result = await alerts.get_cyclone_alerts(10.0, 76.0)
    assert result.is_cached is True
    assert result.data["cyclone_alerts"] == []
