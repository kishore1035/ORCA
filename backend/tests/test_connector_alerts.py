import httpx
import respx
from app.connectors import alerts


async def test_get_lightning_alerts_returns_cached_snapshot():
    result = await alerts.get_lightning_alerts(10.0, 76.0)
    assert result.is_cached is True
    assert result.source == "cached-lightning-snapshot"
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
