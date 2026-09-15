from app.agents import route_agent as ra


def test_bearing_deg_due_east():
    bearing = ra._bearing_deg(10.0, 76.0, 10.0, 77.0)
    assert 85 < bearing < 95


def test_bearing_deg_due_north():
    bearing = ra._bearing_deg(10.0, 76.0, 11.0, 76.0)
    assert bearing < 5 or bearing > 355


def test_interpolate_waypoints_includes_start_and_end():
    waypoints = ra._interpolate_waypoints(10.0, 76.0, 11.0, 77.0, 5)
    assert len(waypoints) == 5
    assert waypoints[0] == (10.0, 76.0)
    assert waypoints[-1] == (11.0, 77.0)


def test_offset_perpendicular_moves_the_point():
    lat, lon = ra._offset_perpendicular(10.0, 76.0, 90.0, 20.0)
    assert (lat, lon) != (10.0, 76.0)


async def test_run_route_agent_all_safe_waypoints(monkeypatch):
    async def fake_check_waypoint(lat, lon):
        return {"lat": lat, "lon": lon, "verdict": "safe", "reasons": ["calm"]}

    monkeypatch.setattr(ra, "_check_waypoint", fake_check_waypoint)

    output, trace = await ra.run_route_agent(10.0, 76.0, 10.5, 76.5)

    assert output["overall_verdict"] == "safe"
    assert len(output["waypoints"]) == ra.WAYPOINT_COUNT
    assert all(w["verdict"] == "safe" for w in output["waypoints"])
    assert trace.agent == "route"


async def test_run_route_agent_flags_hazardous_segment_with_detour(monkeypatch):
    call_count = {"n": 0}

    async def fake_check_waypoint(lat, lon):
        call_count["n"] += 1
        # First call (waypoint 0) is unsafe; every other call (including the
        # detour re-check) is safe.
        if call_count["n"] == 1:
            return {"lat": lat, "lon": lon, "verdict": "unsafe", "reasons": ["high waves"]}
        return {"lat": lat, "lon": lon, "verdict": "safe", "reasons": ["calm"]}

    monkeypatch.setattr(ra, "_check_waypoint", fake_check_waypoint)

    output, _ = await ra.run_route_agent(10.0, 76.0, 10.5, 76.5)

    assert output["overall_verdict"] == "hazardous_segments"
    first = output["waypoints"][0]
    assert first["verdict"] == "unsafe"
    assert first["detour"] is not None
    assert first["detour"]["verdict"] == "safe"


async def test_run_route_agent_detour_none_when_detour_also_unsafe(monkeypatch):
    async def fake_check_waypoint(lat, lon):
        return {"lat": lat, "lon": lon, "verdict": "unsafe", "reasons": ["storm"]}

    monkeypatch.setattr(ra, "_check_waypoint", fake_check_waypoint)

    output, _ = await ra.run_route_agent(10.0, 76.0, 10.5, 76.5)

    assert output["waypoints"][0]["detour"] is None
