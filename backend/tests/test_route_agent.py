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


def test_sample_waypoints_keeps_all_when_under_max():
    coords = [(1.0, 1.0), (2.0, 2.0), (3.0, 3.0)]
    assert ra._sample_waypoints(coords, max_count=5) == coords


def test_sample_waypoints_always_includes_first_and_last():
    coords = [(float(i), float(i)) for i in range(20)]
    sampled = ra._sample_waypoints(coords, max_count=5)
    assert len(sampled) == 5
    assert sampled[0] == coords[0]
    assert sampled[-1] == coords[-1]


def test_compute_sea_route_returns_none_for_degenerate_result(monkeypatch):
    monkeypatch.setattr(
        ra, "_searoute_raw",
        lambda start_lon, start_lat, end_lon, end_lat: {
            "geometry": {"coordinates": [[76.2, 9.9]]},
            "properties": {"length": 0},
        },
    )
    assert ra._compute_sea_route(9.9, 76.2, 9.5, 76.3) is None


def test_compute_sea_route_returns_lat_lon_tuples_for_real_route(monkeypatch):
    monkeypatch.setattr(
        ra, "_searoute_raw",
        lambda start_lon, start_lat, end_lon, end_lat: {
            "geometry": {"coordinates": [[72.8, 18.9], [74.1, 12.7], [76.2, 9.9]]},
            "properties": {"length": 1230.8},
        },
    )
    route = ra._compute_sea_route(18.9, 72.8, 9.9, 76.2)
    assert route == [(18.9, 72.8), (12.7, 74.1), (9.9, 76.2)]


async def test_run_route_agent_uses_sea_route_waypoints_when_available(monkeypatch):
    monkeypatch.setattr(
        ra, "_compute_sea_route",
        lambda sl, so, el, eo: [(18.9, 72.8), (15.0, 74.0), (12.7, 74.1), (9.9, 76.2)],
    )

    async def fake_check_waypoint(lat, lon):
        return {"lat": lat, "lon": lon, "verdict": "safe", "reasons": ["calm"]}

    monkeypatch.setattr(ra, "_check_waypoint", fake_check_waypoint)

    output, trace = await ra.run_route_agent(18.9, 72.8, 9.9, 76.2)

    assert output["route_source"] == "shipping_lanes"
    assert len(output["waypoints"]) == 4
    assert output["waypoints"][0]["lat"] == 18.9


async def test_run_route_agent_falls_back_to_direct_line_when_no_sea_route(monkeypatch):
    monkeypatch.setattr(ra, "_compute_sea_route", lambda sl, so, el, eo: None)

    async def fake_check_waypoint(lat, lon):
        return {"lat": lat, "lon": lon, "verdict": "safe", "reasons": ["calm"]}

    monkeypatch.setattr(ra, "_check_waypoint", fake_check_waypoint)

    output, trace = await ra.run_route_agent(10.0, 76.0, 10.5, 76.5)

    assert output["route_source"] == "direct_line_fallback"
    assert len(output["waypoints"]) == ra.WAYPOINT_COUNT
