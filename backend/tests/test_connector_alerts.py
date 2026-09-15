from app.connectors import alerts


async def test_get_alerts_returns_cached_snapshot():
    result = await alerts.get_alerts(10.0, 76.0)
    assert result.is_cached is True
    assert result.source == "cached-alerts-snapshot"
    assert "cyclone_alerts" in result.data
    assert "lightning_alerts" in result.data
