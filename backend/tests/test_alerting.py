import asyncio
from app import alerting, db


async def test_subscribe_publish_delivers_to_queue():
    queue = alerting.subscribe("s1")
    try:
        alerting.publish("s1", {"type": "alert", "message": "test"})
        item = await asyncio.wait_for(queue.get(), timeout=1)
        assert item == {"type": "alert", "message": "test"}
    finally:
        alerting.unsubscribe("s1", queue)


async def test_publish_with_no_subscriber_is_a_noop():
    # Should not raise even though nobody is listening for this session.
    alerting.publish("no-such-session", {"type": "alert", "message": "test"})


async def test_unsubscribe_stops_delivery():
    queue = alerting.subscribe("s2")
    alerting.unsubscribe("s2", queue)
    alerting.publish("s2", {"type": "alert", "message": "test"})
    assert queue.empty()


async def test_check_hazards_once_alerts_on_transition_to_unsafe(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.set_last_location("s3", 9.9679, 76.2444)
    db.set_last_verdict("s3", "safe")

    async def fake_run_weather_agent(lat, lon):
        return {"wave_height_m": 3.0, "wind_speed_kmh": 10.0}, None

    async def fake_run_risk_agent(lat, lon, weather):
        return {"verdict": "unsafe", "reasons": ["Wave height 3.0m exceeds safe threshold"]}, None

    monkeypatch.setattr(alerting, "run_weather_agent", fake_run_weather_agent)
    monkeypatch.setattr(alerting, "run_risk_agent", fake_run_risk_agent)

    queue = alerting.subscribe("s3")
    try:
        await alerting.check_hazards_once()
        item = await asyncio.wait_for(queue.get(), timeout=1)
        assert item["type"] == "alert"
        assert "Wave height" in item["reasons"][0]
    finally:
        alerting.unsubscribe("s3", queue)

    assert db.get_last_verdict("s3") == "unsafe"


async def test_check_hazards_once_does_not_realert_while_still_unsafe(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.set_last_location("s4", 9.9679, 76.2444)
    db.set_last_verdict("s4", "unsafe")

    async def fake_run_weather_agent(lat, lon):
        return {"wave_height_m": 3.0, "wind_speed_kmh": 10.0}, None

    async def fake_run_risk_agent(lat, lon, weather):
        return {"verdict": "unsafe", "reasons": ["still bad"]}, None

    monkeypatch.setattr(alerting, "run_weather_agent", fake_run_weather_agent)
    monkeypatch.setattr(alerting, "run_risk_agent", fake_run_risk_agent)

    queue = alerting.subscribe("s4")
    try:
        await alerting.check_hazards_once()
        assert queue.empty()
    finally:
        alerting.unsubscribe("s4", queue)


async def test_check_hazards_once_updates_verdict_without_alerting_when_still_safe(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    db.set_last_location("s5", 9.9679, 76.2444)
    db.set_last_verdict("s5", "safe")

    async def fake_run_weather_agent(lat, lon):
        return {"wave_height_m": 1.0, "wind_speed_kmh": 10.0}, None

    async def fake_run_risk_agent(lat, lon, weather):
        return {"verdict": "safe", "reasons": ["calm"]}, None

    monkeypatch.setattr(alerting, "run_weather_agent", fake_run_weather_agent)
    monkeypatch.setattr(alerting, "run_risk_agent", fake_run_risk_agent)

    queue = alerting.subscribe("s5")
    try:
        await alerting.check_hazards_once()
        assert queue.empty()
    finally:
        alerting.unsubscribe("s5", queue)

    assert db.get_last_verdict("s5") == "safe"
