import httpx
import respx
from app.connectors import pfz

SAMPLE_TABLE_HTML = """
<table border="1px" class="center">
  <tr>
    <th>From the coast of</th>
    <th>Direction</th>
    <th>Bearing (deg)</th>
    <th>Distance (km)<br>From-To</th>
    <th>Depth (mtr)<br>From-To</th>
    <th>Latitude (dms)</th>
    <th>Longitude (dms)</th>
  </tr>
  <tr>
    <td align="center">Kunzhathur</td>
    <td align="center">SW</td>
    <td align="center">265</td>
    <td align="center">42-47</td>
    <td align="center">50-55</td>
    <td align="center">12 42 36 N</td>
    <td align="center">74 27 53 E</td>
  </tr>
  <tr>
    <td align="center">Manjeshwara</td>
    <td align="center">SW</td>
    <td align="center">264</td>
    <td align="center">45-50</td>
    <td align="center">53-58</td>
    <td align="center">12 40 1 N</td>
    <td align="center">74 27 32 E</td>
  </tr>
</table>
"""


def test_parse_dms_north_and_east_are_positive():
    assert pfz._parse_dms("12 42 36 N") == 12 + 42 / 60 + 36 / 3600
    assert pfz._parse_dms("74 27 53 E") == 74 + 27 / 60 + 53 / 3600


def test_parse_dms_south_and_west_are_negative():
    assert pfz._parse_dms("12 42 36 S") < 0
    assert pfz._parse_dms("74 27 53 W") < 0


def test_parse_range_splits_low_high():
    assert pfz._parse_range("42-47") == [42.0, 47.0]


def test_parse_landing_centers_skips_header_row():
    centers = pfz._parse_landing_centers(SAMPLE_TABLE_HTML)
    assert len(centers) == 2
    assert centers[0]["name"] == "Kunzhathur"
    assert centers[0]["bearing_deg"] == 265
    assert centers[0]["offshore_distance_km_range"] == [42.0, 47.0]


@respx.mock
async def test_get_pfz_advisory_live_success_picks_nearest_center():
    respx.get("https://nominatim.openstreetmap.org/reverse").mock(
        return_value=httpx.Response(200, json={"address": {"state": "Kerala"}})
    )
    respx.get(pfz.TEXT_DATA_HOME_URL).mock(return_value=httpx.Response(200, text="<html></html>"))
    respx.get(pfz.TEXT_DATA_URL).mock(return_value=httpx.Response(200, text=SAMPLE_TABLE_HTML))

    result = await pfz.get_pfz_advisory(12.71, 74.464)

    assert result.is_cached is False
    assert result.data["sector"] == "SEC005"
    assert result.data["nearest_landing_center"] == "Kunzhathur"


@respx.mock
async def test_get_pfz_advisory_splits_tamil_nadu_by_latitude():
    respx.get("https://nominatim.openstreetmap.org/reverse").mock(
        return_value=httpx.Response(200, json={"address": {"state": "Tamil Nadu"}})
    )
    respx.get(pfz.TEXT_DATA_HOME_URL).mock(return_value=httpx.Response(200, text="<html></html>"))
    respx.get(pfz.TEXT_DATA_URL).mock(return_value=httpx.Response(200, text=SAMPLE_TABLE_HTML))

    north = await pfz.get_pfz_advisory(13.0, 80.2)
    south = await pfz.get_pfz_advisory(9.0, 78.2)

    assert north.data["sector"] == "SEC007"
    assert south.data["sector"] == "SEC006"


@respx.mock
async def test_get_pfz_advisory_falls_back_when_state_has_no_sector():
    respx.get("https://nominatim.openstreetmap.org/reverse").mock(
        return_value=httpx.Response(200, json={"address": {"state": "Rajasthan"}})
    )
    result = await pfz.get_pfz_advisory(26.9, 75.8)
    assert result.is_cached is True
    assert result.data["nearest_landing_center"] is not None


@respx.mock
async def test_get_pfz_advisory_falls_back_on_connection_failure():
    respx.get("https://nominatim.openstreetmap.org/reverse").mock(side_effect=httpx.ConnectError("boom"))
    result = await pfz.get_pfz_advisory(9.9679, 76.2444)
    assert result.is_cached is True
    assert result.data["sector"] == "SEC005"
