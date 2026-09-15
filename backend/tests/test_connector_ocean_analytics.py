import httpx
import respx
from app.connectors import ocean_analytics


@respx.mock
async def test_get_sst_live_success():
    route = respx.get(url__regex=r"jplMURSST41\.json").mock(
        return_value=httpx.Response(200, json={"table": {"rows": [["2026-09-15T09:00:00Z", 10.0, 76.0, 29.1]]}})
    )
    result = await ocean_analytics.get_sst(10.0, 76.0)
    assert result.is_cached is False
    assert result.data["sst_celsius"] == 29.1

    requested_url = str(route.calls[0].request.url)
    assert "analysed_sst[(" in requested_url
    assert "analysed_sst=" not in requested_url


@respx.mock
async def test_get_sst_falls_back_on_failure():
    respx.get(url__regex=r"jplMURSST41\.json").mock(side_effect=httpx.ConnectError("boom"))
    result = await ocean_analytics.get_sst(10.0, 76.0)
    assert result.is_cached is True
    assert result.data["sst_celsius"] == 28.4


@respx.mock
async def test_get_chlorophyll_live_success():
    route = respx.get(url__regex=r"erdMH1chla1day\.json").mock(
        return_value=httpx.Response(200, json={"table": {"rows": [["2026-09-15T00:00:00Z", 10.0, 76.0, 0.42]]}})
    )
    result = await ocean_analytics.get_chlorophyll(10.0, 76.0)
    assert result.is_cached is False
    assert result.data["chlorophyll_mg_m3"] == 0.42

    requested_url = str(route.calls[0].request.url)
    assert "chlorophyll[(" in requested_url
    assert "chlorophyll=" not in requested_url


@respx.mock
async def test_get_sst_trend_live_success():
    route = respx.get(url__regex=r"jplMURSST41\.json").mock(
        return_value=httpx.Response(
            200,
            json={
                "table": {
                    "rows": [
                        ["2026-09-08T09:00:00Z", 10.0, 76.0, 28.0],
                        ["2026-09-09T09:00:00Z", 10.0, 76.0, 28.5],
                        ["2026-09-10T09:00:00Z", 10.0, 76.0, 29.0],
                    ]
                }
            },
        )
    )
    result = await ocean_analytics.get_sst_trend(10.0, 76.0)
    assert result.is_cached is False
    assert result.data["sst_trend"] == [
        {"date": "2026-09-08T09:00:00Z", "sst_celsius": 28.0},
        {"date": "2026-09-09T09:00:00Z", "sst_celsius": 28.5},
        {"date": "2026-09-10T09:00:00Z", "sst_celsius": 29.0},
    ]

    requested_url = str(route.calls[0].request.url)
    assert "analysed_sst[(" in requested_url
    assert "analysed_sst=" not in requested_url
    assert ":1:" in requested_url


@respx.mock
async def test_get_sst_trend_falls_back_on_failure():
    respx.get(url__regex=r"jplMURSST41\.json").mock(side_effect=httpx.ConnectError("boom"))
    result = await ocean_analytics.get_sst_trend(10.0, 76.0)
    assert result.is_cached is True
    assert len(result.data["sst_trend"]) > 0
    assert "sst_celsius" in result.data["sst_trend"][0]
