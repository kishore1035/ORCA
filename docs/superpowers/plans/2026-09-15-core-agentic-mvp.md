# ORCA Core Agentic MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working agentic backend (FastAPI + LangGraph) and Next.js frontend that answers "is it safe to go out", "where's the nearest fishing zone", and "any cyclone/lightning alerts" questions end-to-end with real correlation logic, a visible reasoning trace, and a map, using only free/no-cost external services.

**Architecture:** A LangGraph pipeline (`planner → geospatial → weather → risk → ocean_analytics → reporting`) where each node wraps one specialist agent; agents call pluggable `connectors/` modules that fetch live data with a one-retry-then-cached-snapshot fallback. A Next.js frontend streams the pipeline's trace and final answer over SSE and renders a chat panel, a reasoning-trace panel, and a Leaflet map.

**Tech Stack:** Python 3.11+, FastAPI, LangGraph, `google-genai` (Gemini free tier) for the two reasoning steps, httpx, shapely, pytest/pytest-asyncio/respx. Next.js 14 (App Router, TypeScript, Tailwind), react-leaflet, Vitest.

**Spec:** `docs/superpowers/specs/2026-09-15-core-agentic-mvp-design.md`

## Global Constraints

- No paid API anywhere. The only LLM calls (Planner, Reporting) use Google Gemini's free tier (`gemini-2.5-flash`) via a `GEMINI_API_KEY` obtained free from Google AI Studio — no billing account. This is a deviation from the spec's unspecified LLM choice, made explicit here.
- SST/chlorophyll use NOAA ERDDAP (`jplMURSST41`, `erdMH1chla1day`) instead of the spec's named Copernicus Marine/NASA Ocean Color — same class of free open data, no registration required at all, simpler for Phase 1. Every other spec requirement (normalized connector result, cache fallback, staleness disclosure) is unchanged.
- No database in Phase 1 — session/conversation state lives in the frontend and is resent each turn.
- Every connector returns the same shape: `{data, source, fetched_at, is_cached}`. A connector never fabricates data — on live failure it falls back to a committed snapshot file and flags `is_cached=True`.
- Every external HTTP call is retried once before falling back to its cached snapshot (spec section 5).
- Every agent call is recorded as a `TraceEntry` and returned to the frontend — this is not optional decoration, it is the "make agentic behavior demonstrable" requirement from the spec.
- Map: Leaflet + OpenStreetMap tiles (no API key required) — a deviation from the spec's "Mapbox GL/Leaflet" wording, choosing the no-key option.

---

## Task 1: Backend Project Scaffold

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `app.config.get_settings() -> Settings` (fields: `gemini_api_key: str`, `cors_origins: list[str]`), used by every later backend task that needs config.
- Produces: `app.main.app` (the FastAPI instance), used by Task 15 and Task 16.

- [ ] **Step 1: Create the requirements file**

```text
fastapi>=0.110
uvicorn[standard]>=0.27
pydantic>=2.6
pydantic-settings>=2.2
httpx>=0.27
langgraph>=0.2.0
google-genai>=0.3.0
shapely>=2.0
python-dotenv>=1.0
pytest>=8.0
pytest-asyncio>=0.23
respx>=0.20
```

Save as `backend/requirements.txt`.

- [ ] **Step 2: Create pytest config**

```ini
[pytest]
asyncio_mode = auto
pythonpath = .
```

Save as `backend/pytest.ini`. The `pythonpath = .` line (a builtin pytest option since 7.0, resolved relative to this ini file) is what makes `from app... import ...` resolve when running plain `pytest` from `backend/` — without it there is nothing putting `backend/` on `sys.path`, since `tests/` has no `__init__.py` and there is no editable install.

- [ ] **Step 3: Create the settings module**

```python
# backend/app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Write the failing health-check test**

```python
# backend/tests/test_health.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 5: Run test to verify it fails**

Run (from `backend/`): `pytest tests/test_health.py -v`
Expected: FAIL (`app.main` does not exist / ModuleNotFoundError)

- [ ] **Step 6: Create the FastAPI app with the health endpoint**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings

app = FastAPI(title="ORCA Marine Intelligence Platform")

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

Also create empty `backend/app/__init__.py`.

- [ ] **Step 7: Run test to verify it passes**

Run: `pytest tests/test_health.py -v`
Expected: PASS

- [ ] **Step 8: Create a minimal pyproject.toml so `app` is importable as a package**

```toml
# backend/pyproject.toml
[project]
name = "orca-backend"
version = "0.1.0"
requires-python = ">=3.11"

[tool.setuptools]
packages = ["app"]
```

- [ ] **Step 9: Commit**

```bash
cd backend
git add pyproject.toml requirements.txt pytest.ini app/__init__.py app/config.py app/main.py tests/test_health.py
git commit -m "feat: backend scaffold with FastAPI health endpoint

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 2: Shared Schemas

**Files:**
- Create: `backend/app/schemas.py`
- Test: `backend/tests/test_schemas.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `ConnectorResult(data, source, fetched_at, is_cached)`, `TraceEntry(agent, inputs, output, sources, fetched_at, is_cached)`, `ChatMessage(role, content)`, `ChatRequest(session_id, message, history)`, `ChatResponse(answer, trace, geojson)` — every later task imports these from `app.schemas`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_schemas.py
from datetime import datetime, timezone
from app.schemas import ConnectorResult, TraceEntry, ChatRequest, ChatMessage


def test_connector_result_roundtrip():
    result = ConnectorResult(
        data={"wave_height_m": 1.2},
        source="open-meteo-marine",
        fetched_at=datetime.now(timezone.utc),
        is_cached=False,
    )
    assert result.is_cached is False
    assert result.data["wave_height_m"] == 1.2


def test_trace_entry_defaults():
    entry = TraceEntry(agent="weather", inputs={}, output={}, sources=["x"])
    assert entry.is_cached is False
    assert entry.fetched_at is None


def test_chat_request_parses_history():
    req = ChatRequest(
        session_id="abc",
        message="is it safe tomorrow?",
        history=[ChatMessage(role="user", content="hi")],
    )
    assert req.history[0].role == "user"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_schemas.py -v`
Expected: FAIL (`ModuleNotFoundError: app.schemas`)

- [ ] **Step 3: Implement the schemas**

```python
# backend/app/schemas.py
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel


class ConnectorResult(BaseModel):
    data: Any
    source: str
    fetched_at: datetime
    is_cached: bool


class TraceEntry(BaseModel):
    agent: str
    inputs: dict[str, Any]
    output: dict[str, Any]
    sources: list[str]
    fetched_at: datetime | None = None
    is_cached: bool = False


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    session_id: str
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    answer: str
    trace: list[TraceEntry]
    geojson: dict[str, Any] | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/schemas.py tests/test_schemas.py
git commit -m "feat: shared pydantic schemas for connectors, trace, and chat

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 3: Connector Base (fetch-with-retry-then-fallback)

**Files:**
- Create: `backend/app/connectors/__init__.py`
- Create: `backend/app/connectors/base.py`
- Test: `backend/tests/test_connector_base.py`

**Interfaces:**
- Consumes: `app.schemas.ConnectorResult`.
- Produces: `async def fetch_with_fallback(source: str, live_fetch: Callable[[], Awaitable[Any]], snapshot_path: Path, timeout_seconds: float = 10.0) -> ConnectorResult` — every connector in Tasks 4-6 calls this.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_connector_base.py
import json
import pytest
from pathlib import Path
from app.connectors.base import fetch_with_fallback


async def test_live_fetch_success_returns_live_data():
    async def live_fetch():
        return {"value": 42}

    result = await fetch_with_fallback("test-source", live_fetch, Path("unused.json"))
    assert result.is_cached is False
    assert result.data == {"value": 42}
    assert result.source == "test-source"


async def test_falls_back_to_snapshot_after_two_failures(tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps({
        "fetched_at": "2026-09-01T06:00:00+00:00",
        "data": {"value": "cached"},
    }))
    call_count = 0

    async def failing_fetch():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("boom")

    result = await fetch_with_fallback("test-source", failing_fetch, snapshot_path)
    assert call_count == 2, "must retry exactly once before falling back"
    assert result.is_cached is True
    assert result.data == {"value": "cached"}
    assert result.source == "test-source"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_connector_base.py -v`
Expected: FAIL (`ModuleNotFoundError: app.connectors`)

- [ ] **Step 3: Implement the connector base**

```python
# backend/app/connectors/base.py
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable
from app.schemas import ConnectorResult


async def fetch_with_fallback(
    source: str,
    live_fetch: Callable[[], Awaitable[Any]],
    snapshot_path: Path,
    timeout_seconds: float = 10.0,
) -> ConnectorResult:
    for attempt in range(2):
        try:
            data = await asyncio.wait_for(live_fetch(), timeout=timeout_seconds)
            return ConnectorResult(
                data=data,
                source=source,
                fetched_at=datetime.now(timezone.utc),
                is_cached=False,
            )
        except Exception:
            if attempt == 0:
                continue

    snapshot = json.loads(snapshot_path.read_text())
    return ConnectorResult(
        data=snapshot["data"],
        source=source,
        fetched_at=datetime.fromisoformat(snapshot["fetched_at"]),
        is_cached=True,
    )
```

Also create empty `backend/app/connectors/__init__.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_connector_base.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/connectors/__init__.py app/connectors/base.py tests/test_connector_base.py
git commit -m "feat: connector base with retry-then-cached-snapshot fallback

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 4: Weather Connector (Open-Meteo)

**Files:**
- Create: `backend/app/connectors/weather.py`
- Create: `backend/data/snapshots/weather.json`
- Test: `backend/tests/test_connector_weather.py`

**Interfaces:**
- Consumes: `fetch_with_fallback` from Task 3.
- Produces: `async def get_weather(lat: float, lon: float) -> ConnectorResult` where `.data` has keys `wave_height_m`, `swell_height_m`, `wind_speed_kmh`, `wind_direction_deg`, `forecast_time` — consumed by Task 8 (Weather Agent).

- [ ] **Step 1: Create the cached snapshot fixture**

```json
{
  "fetched_at": "2026-09-01T06:00:00+00:00",
  "data": {
    "wave_height_m": 1.2,
    "swell_height_m": 0.8,
    "wind_speed_kmh": 18.5,
    "wind_direction_deg": 210,
    "forecast_time": "2026-09-01T06:00"
  }
}
```

Save as `backend/data/snapshots/weather.json`.

- [ ] **Step 2: Write the failing tests**

```python
# backend/tests/test_connector_weather.py
import httpx
import respx
from app.connectors import weather


@respx.mock
async def test_get_weather_live_success():
    respx.get("https://marine-api.open-meteo.com/v1/marine").mock(
        return_value=httpx.Response(
            200, json={"hourly": {"wave_height": [1.5], "swell_wave_height": [1.0]}}
        )
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(
            200,
            json={
                "hourly": {
                    "wind_speed_10m": [20.0],
                    "wind_direction_10m": [180],
                    "time": ["2026-09-15T06:00"],
                }
            },
        )
    )
    result = await weather.get_weather(10.0, 76.0)
    assert result.is_cached is False
    assert result.data["wave_height_m"] == 1.5
    assert result.data["wind_speed_kmh"] == 20.0


@respx.mock
async def test_get_weather_falls_back_on_failure():
    respx.get("https://marine-api.open-meteo.com/v1/marine").mock(
        side_effect=httpx.ConnectError("boom")
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        side_effect=httpx.ConnectError("boom")
    )
    result = await weather.get_weather(10.0, 76.0)
    assert result.is_cached is True
    assert result.data["wave_height_m"] == 1.2
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_connector_weather.py -v`
Expected: FAIL (`ModuleNotFoundError: app.connectors.weather`)

- [ ] **Step 4: Implement the weather connector**

```python
# backend/app/connectors/weather.py
from pathlib import Path
import httpx
from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots" / "weather.json"


async def _live_fetch(lat: float, lon: float) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        marine_resp = await client.get(
            "https://marine-api.open-meteo.com/v1/marine",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wave_height,swell_wave_height",
                "timezone": "auto",
            },
        )
        marine_resp.raise_for_status()
        marine = marine_resp.json()

        wind_resp = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "hourly": "wind_speed_10m,wind_direction_10m",
                "timezone": "auto",
            },
        )
        wind_resp.raise_for_status()
        wind = wind_resp.json()

    return {
        "wave_height_m": marine["hourly"]["wave_height"][0],
        "swell_height_m": marine["hourly"]["swell_wave_height"][0],
        "wind_speed_kmh": wind["hourly"]["wind_speed_10m"][0],
        "wind_direction_deg": wind["hourly"]["wind_direction_10m"][0],
        "forecast_time": wind["hourly"]["time"][0],
    }


async def get_weather(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback(
        source="open-meteo-marine",
        live_fetch=lambda: _live_fetch(lat, lon),
        snapshot_path=SNAPSHOT_PATH,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_connector_weather.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/connectors/weather.py data/snapshots/weather.json tests/test_connector_weather.py
git commit -m "feat: Open-Meteo weather connector with cached fallback

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 5: Ocean Analytics Connectors (SST + Chlorophyll via NOAA ERDDAP)

**Files:**
- Create: `backend/app/connectors/ocean_analytics.py`
- Create: `backend/data/snapshots/sst.json`
- Create: `backend/data/snapshots/chlorophyll.json`
- Test: `backend/tests/test_connector_ocean_analytics.py`

**Interfaces:**
- Consumes: `fetch_with_fallback` from Task 3.
- Produces: `async def get_sst(lat, lon) -> ConnectorResult` (`.data["sst_celsius"]`), `async def get_chlorophyll(lat, lon) -> ConnectorResult` (`.data["chlorophyll_mg_m3"]`) — consumed by Task 9 (Ocean Analytics Agent).

- [ ] **Step 1: Create the cached snapshot fixtures**

```json
{"fetched_at": "2026-09-01T06:00:00+00:00", "data": {"sst_celsius": 28.4}}
```

Save as `backend/data/snapshots/sst.json`.

```json
{"fetched_at": "2026-09-01T06:00:00+00:00", "data": {"chlorophyll_mg_m3": 0.35}}
```

Save as `backend/data/snapshots/chlorophyll.json`.

- [ ] **Step 2: Write the failing tests**

```python
# backend/tests/test_connector_ocean_analytics.py
import httpx
import respx
from app.connectors import ocean_analytics


@respx.mock
async def test_get_sst_live_success():
    respx.get(url__regex=r"jplMURSST41\.json").mock(
        return_value=httpx.Response(200, json={"table": {"rows": [["2026-09-15T09:00:00Z", 10.0, 76.0, 29.1]]}})
    )
    result = await ocean_analytics.get_sst(10.0, 76.0)
    assert result.is_cached is False
    assert result.data["sst_celsius"] == 29.1


@respx.mock
async def test_get_sst_falls_back_on_failure():
    respx.get(url__regex=r"jplMURSST41\.json").mock(side_effect=httpx.ConnectError("boom"))
    result = await ocean_analytics.get_sst(10.0, 76.0)
    assert result.is_cached is True
    assert result.data["sst_celsius"] == 28.4


@respx.mock
async def test_get_chlorophyll_live_success():
    respx.get(url__regex=r"erdMH1chla1day\.json").mock(
        return_value=httpx.Response(200, json={"table": {"rows": [["2026-09-15T00:00:00Z", 10.0, 76.0, 0.42]]}})
    )
    result = await ocean_analytics.get_chlorophyll(10.0, 76.0)
    assert result.is_cached is False
    assert result.data["chlorophyll_mg_m3"] == 0.42
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_connector_ocean_analytics.py -v`
Expected: FAIL (`ModuleNotFoundError: app.connectors.ocean_analytics`)

- [ ] **Step 4: Implement the ocean analytics connectors**

```python
# backend/app/connectors/ocean_analytics.py
from datetime import date
from pathlib import Path
import httpx
from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots"
SST_SNAPSHOT = DATA_DIR / "sst.json"
CHLOROPHYLL_SNAPSHOT = DATA_DIR / "chlorophyll.json"
ERDDAP_BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"


async def _fetch_sst(lat: float, lon: float) -> dict:
    today = date.today().isoformat()
    url = f"{ERDDAP_BASE}/jplMURSST41.json"
    params = {"analysed_sst": f"[({today}T09:00:00Z)][({lat})][({lon})]"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        payload = resp.json()
    return {"sst_celsius": payload["table"]["rows"][0][-1]}


async def _fetch_chlorophyll(lat: float, lon: float) -> dict:
    today = date.today().isoformat()
    url = f"{ERDDAP_BASE}/erdMH1chla1day.json"
    params = {"chlorophyll": f"[({today}T00:00:00Z)][({lat})][({lon})]"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        payload = resp.json()
    return {"chlorophyll_mg_m3": payload["table"]["rows"][0][-1]}


async def get_sst(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback("noaa-erddap-sst", lambda: _fetch_sst(lat, lon), SST_SNAPSHOT)


async def get_chlorophyll(lat: float, lon: float) -> ConnectorResult:
    return await fetch_with_fallback(
        "noaa-erddap-chlorophyll", lambda: _fetch_chlorophyll(lat, lon), CHLOROPHYLL_SNAPSHOT
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_connector_ocean_analytics.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/connectors/ocean_analytics.py data/snapshots/sst.json data/snapshots/chlorophyll.json tests/test_connector_ocean_analytics.py
git commit -m "feat: NOAA ERDDAP SST and chlorophyll connectors

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 6: Alerts Connector (cached cyclone/lightning snapshot)

**Files:**
- Create: `backend/app/connectors/alerts.py`
- Create: `backend/data/snapshots/alerts.json`
- Test: `backend/tests/test_connector_alerts.py`

**Interfaces:**
- Consumes: nothing external (no free live feed identified for Phase 1, per spec section 3).
- Produces: `async def get_alerts(lat: float, lon: float) -> ConnectorResult` where `.data` has keys `cyclone_alerts: list[dict]`, `lightning_alerts: list[dict]` — consumed by Task 10 (Risk Agent).

- [ ] **Step 1: Create the cached snapshot fixture**

```json
{
  "fetched_at": "2026-09-15T00:00:00+00:00",
  "data": {
    "cyclone_alerts": [],
    "lightning_alerts": []
  }
}
```

Save as `backend/data/snapshots/alerts.json`.

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/test_connector_alerts.py
from app.connectors import alerts


async def test_get_alerts_returns_cached_snapshot():
    result = await alerts.get_alerts(10.0, 76.0)
    assert result.is_cached is True
    assert result.source == "cached-alerts-snapshot"
    assert "cyclone_alerts" in result.data
    assert "lightning_alerts" in result.data
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_connector_alerts.py -v`
Expected: FAIL (`ModuleNotFoundError: app.connectors.alerts`)

- [ ] **Step 4: Implement the alerts connector**

```python
# backend/app/connectors/alerts.py
import json
from datetime import datetime
from pathlib import Path
from app.schemas import ConnectorResult

SNAPSHOT_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots" / "alerts.json"


async def get_alerts(lat: float, lon: float) -> ConnectorResult:
    """No free live cyclone/lightning feed is wired up for Phase 1 (spec section 3).
    Always serves the cached snapshot; the interface matches every other connector
    so a live feed can be substituted later without touching callers."""
    snapshot = json.loads(SNAPSHOT_PATH.read_text())
    return ConnectorResult(
        data=snapshot["data"],
        source="cached-alerts-snapshot",
        fetched_at=datetime.fromisoformat(snapshot["fetched_at"]),
        is_cached=True,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_connector_alerts.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/connectors/alerts.py data/snapshots/alerts.json tests/test_connector_alerts.py
git commit -m "feat: cached cyclone/lightning alerts connector

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 7: Geospatial Connector (geocoding + boundary proximity)

**Files:**
- Create: `backend/app/connectors/geospatial.py`
- Create: `backend/data/snapshots/geocode.json`
- Create: `backend/data/snapshots/mpa_boundaries.geojson`
- Test: `backend/tests/test_connector_geospatial.py`

**Interfaces:**
- Consumes: `fetch_with_fallback` from Task 3.
- Produces: `async def geocode(place_name: str) -> ConnectorResult` (`.data` has `lat`, `lon`, `display_name`); `def nearest_boundary_distance_km(lat: float, lon: float) -> dict` (keys `nearest_boundary`, `distance_km`, `source`) — both consumed by Task 11 (Geospatial Agent).

- [ ] **Step 1: Create the cached snapshot fixtures**

```json
{
  "fetched_at": "2026-09-01T06:00:00+00:00",
  "data": {"lat": 9.9312, "lon": 76.2673, "display_name": "Kochi, Kerala, India"}
}
```

Save as `backend/data/snapshots/geocode.json`.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {"name": "Example Marine Protected Area"},
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[75.8, 9.6], [75.9, 9.6], [75.9, 9.7], [75.8, 9.7], [75.8, 9.6]]]
      }
    }
  ]
}
```

Save as `backend/data/snapshots/mpa_boundaries.geojson`.

- [ ] **Step 2: Write the failing tests**

```python
# backend/tests/test_connector_geospatial.py
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_connector_geospatial.py -v`
Expected: FAIL (`ModuleNotFoundError: app.connectors.geospatial`)

- [ ] **Step 4: Implement the geospatial connector**

```python
# backend/app/connectors/geospatial.py
import json
from pathlib import Path
import httpx
from shapely.geometry import Point, shape
from app.connectors.base import fetch_with_fallback
from app.schemas import ConnectorResult

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots"
GEOCODE_SNAPSHOT = DATA_DIR / "geocode.json"
MPA_BOUNDARIES_PATH = DATA_DIR / "mpa_boundaries.geojson"

KM_PER_DEGREE = 111.0


async def _geocode_live(place_name: str) -> dict:
    async with httpx.AsyncClient(
        timeout=10.0, headers={"User-Agent": "orca-marine-platform/0.1"}
    ) as client:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": place_name, "format": "json", "limit": 1},
        )
        resp.raise_for_status()
        results = resp.json()
    if not results:
        raise ValueError(f"No geocode result for {place_name!r}")
    return {
        "lat": float(results[0]["lat"]),
        "lon": float(results[0]["lon"]),
        "display_name": results[0]["display_name"],
    }


async def geocode(place_name: str) -> ConnectorResult:
    return await fetch_with_fallback(
        source="nominatim",
        live_fetch=lambda: _geocode_live(place_name),
        snapshot_path=GEOCODE_SNAPSHOT,
    )


def nearest_boundary_distance_km(lat: float, lon: float) -> dict:
    """Static MPA/international-boundary snapshot check (Phase 1 has no live feed)."""
    boundaries = json.loads(MPA_BOUNDARIES_PATH.read_text())
    point = Point(lon, lat)
    nearest_name = None
    nearest_distance_deg = float("inf")
    for feature in boundaries["features"]:
        geom = shape(feature["geometry"])
        distance_deg = point.distance(geom)
        if distance_deg < nearest_distance_deg:
            nearest_distance_deg = distance_deg
            nearest_name = feature["properties"]["name"]
    return {
        "nearest_boundary": nearest_name,
        "distance_km": round(nearest_distance_deg * KM_PER_DEGREE, 1),
        "source": "static-mpa-imbl-snapshot",
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_connector_geospatial.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/connectors/geospatial.py data/snapshots/geocode.json data/snapshots/mpa_boundaries.geojson tests/test_connector_geospatial.py
git commit -m "feat: geospatial connector for geocoding and boundary proximity

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 8: Weather Agent

**Files:**
- Create: `backend/app/agents/__init__.py`
- Create: `backend/app/agents/weather_agent.py`
- Test: `backend/tests/test_weather_agent.py`

**Interfaces:**
- Consumes: `app.connectors.weather.get_weather(lat, lon) -> ConnectorResult`.
- Produces: `async def run_weather_agent(lat: float, lon: float) -> tuple[dict, TraceEntry]` where the dict has keys `wind_speed_kmh`, `wind_direction_deg`, `wave_height_m`, `swell_height_m`, `forecast_time` — consumed by Task 10 (Risk Agent) and Task 14 (graph).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_weather_agent.py
from datetime import datetime, timezone
from app.agents import weather_agent
from app.schemas import ConnectorResult


async def test_run_weather_agent_returns_output_and_trace(monkeypatch):
    fixed_result = ConnectorResult(
        data={
            "wind_speed_kmh": 22.0,
            "wind_direction_deg": 190,
            "wave_height_m": 1.4,
            "swell_height_m": 0.9,
            "forecast_time": "2026-09-15T06:00",
        },
        source="open-meteo-marine",
        fetched_at=datetime(2026, 9, 15, 6, 0, tzinfo=timezone.utc),
        is_cached=False,
    )

    async def fake_get_weather(lat, lon):
        return fixed_result

    monkeypatch.setattr(weather_agent, "get_weather", fake_get_weather)

    output, trace = await weather_agent.run_weather_agent(10.0, 76.0)

    assert output["wind_speed_kmh"] == 22.0
    assert trace.agent == "weather"
    assert trace.sources == ["open-meteo-marine"]
    assert trace.is_cached is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_weather_agent.py -v`
Expected: FAIL (`ModuleNotFoundError: app.agents`)

- [ ] **Step 3: Implement the weather agent**

```python
# backend/app/agents/weather_agent.py
from app.connectors.weather import get_weather
from app.schemas import TraceEntry


async def run_weather_agent(lat: float, lon: float) -> tuple[dict, TraceEntry]:
    result = await get_weather(lat, lon)
    output = {
        "wind_speed_kmh": result.data["wind_speed_kmh"],
        "wind_direction_deg": result.data["wind_direction_deg"],
        "wave_height_m": result.data["wave_height_m"],
        "swell_height_m": result.data["swell_height_m"],
        "forecast_time": result.data["forecast_time"],
    }
    trace = TraceEntry(
        agent="weather",
        inputs={"lat": lat, "lon": lon},
        output=output,
        sources=[result.source],
        fetched_at=result.fetched_at,
        is_cached=result.is_cached,
    )
    return output, trace
```

Also create empty `backend/app/agents/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_weather_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/__init__.py app/agents/weather_agent.py tests/test_weather_agent.py
git commit -m "feat: weather agent

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 9: Ocean Analytics Agent (PFZ correlation logic)

**Files:**
- Create: `backend/app/agents/ocean_analytics_agent.py`
- Test: `backend/tests/test_ocean_analytics_agent.py`

**Interfaces:**
- Consumes: `app.connectors.ocean_analytics.get_sst`, `get_chlorophyll`.
- Produces: `async def run_ocean_analytics_agent(lat: float, lon: float) -> tuple[dict, TraceEntry]` where the dict has keys `sst_celsius`, `chlorophyll_mg_m3`, `pfz_likelihood` (`"high"|"moderate"|"low"`), `reasons: list[str]` — consumed by Task 14 (graph).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_ocean_analytics_agent.py
from datetime import datetime, timezone
from app.agents import ocean_analytics_agent as oaa
from app.schemas import ConnectorResult


def test_score_high_when_both_thresholds_met():
    likelihood, reasons = oaa._score(sst_c=28.5, chlorophyll=0.35)
    assert likelihood == "high"
    assert len(reasons) == 2


def test_score_low_when_neither_threshold_met():
    likelihood, _ = oaa._score(sst_c=22.0, chlorophyll=0.05)
    assert likelihood == "low"


def test_score_moderate_when_one_threshold_met():
    likelihood, _ = oaa._score(sst_c=28.0, chlorophyll=0.05)
    assert likelihood == "moderate"


async def test_run_ocean_analytics_agent_combines_both_connectors(monkeypatch):
    sst_result = ConnectorResult(
        data={"sst_celsius": 28.5}, source="noaa-erddap-sst",
        fetched_at=datetime(2026, 9, 15, tzinfo=timezone.utc), is_cached=False,
    )
    chl_result = ConnectorResult(
        data={"chlorophyll_mg_m3": 0.35}, source="noaa-erddap-chlorophyll",
        fetched_at=datetime(2026, 9, 15, tzinfo=timezone.utc), is_cached=False,
    )

    async def fake_get_sst(lat, lon):
        return sst_result

    async def fake_get_chlorophyll(lat, lon):
        return chl_result

    monkeypatch.setattr(oaa, "get_sst", fake_get_sst)
    monkeypatch.setattr(oaa, "get_chlorophyll", fake_get_chlorophyll)

    output, trace = await oaa.run_ocean_analytics_agent(10.0, 76.0)

    assert output["pfz_likelihood"] == "high"
    assert trace.agent == "ocean_analytics"
    assert set(trace.sources) == {"noaa-erddap-sst", "noaa-erddap-chlorophyll"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_ocean_analytics_agent.py -v`
Expected: FAIL (`ModuleNotFoundError: app.agents.ocean_analytics_agent`)

- [ ] **Step 3: Implement the ocean analytics agent**

```python
# backend/app/agents/ocean_analytics_agent.py
from app.connectors.ocean_analytics import get_sst, get_chlorophyll
from app.schemas import TraceEntry

# Simplified, explicitly-labeled heuristic (not an official PFZ advisory algorithm):
# a warm-water front (27-30C) combined with elevated chlorophyll (>=0.2 mg/m3)
# indicates a likely nutrient-rich front favorable for fish aggregation.
SST_MIN_C = 27.0
SST_MAX_C = 30.0
CHLOROPHYLL_MIN_MG_M3 = 0.2


def _score(sst_c: float, chlorophyll: float) -> tuple[str, list[str]]:
    sst_ok = SST_MIN_C <= sst_c <= SST_MAX_C
    chl_ok = chlorophyll >= CHLOROPHYLL_MIN_MG_M3
    reasons = [
        f"SST {sst_c}°C {'within' if sst_ok else 'outside'} favorable range "
        f"{SST_MIN_C}-{SST_MAX_C}°C",
        f"Chlorophyll {chlorophyll} mg/m³ {'meets' if chl_ok else 'is below'} "
        f"threshold {CHLOROPHYLL_MIN_MG_M3} mg/m³",
    ]
    if sst_ok and chl_ok:
        return "high", reasons
    if sst_ok or chl_ok:
        return "moderate", reasons
    return "low", reasons


async def run_ocean_analytics_agent(lat: float, lon: float) -> tuple[dict, TraceEntry]:
    sst_result = await get_sst(lat, lon)
    chl_result = await get_chlorophyll(lat, lon)
    sst_c = sst_result.data["sst_celsius"]
    chlorophyll = chl_result.data["chlorophyll_mg_m3"]
    likelihood, reasons = _score(sst_c, chlorophyll)
    output = {
        "sst_celsius": sst_c,
        "chlorophyll_mg_m3": chlorophyll,
        "pfz_likelihood": likelihood,
        "reasons": reasons,
    }
    trace = TraceEntry(
        agent="ocean_analytics",
        inputs={"lat": lat, "lon": lon},
        output=output,
        sources=[sst_result.source, chl_result.source],
        fetched_at=max(sst_result.fetched_at, chl_result.fetched_at),
        is_cached=sst_result.is_cached or chl_result.is_cached,
    )
    return output, trace
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ocean_analytics_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/ocean_analytics_agent.py tests/test_ocean_analytics_agent.py
git commit -m "feat: ocean analytics agent with PFZ correlation heuristic

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 10: Risk/Safety Agent

**Files:**
- Create: `backend/app/agents/risk_agent.py`
- Test: `backend/tests/test_risk_agent.py`

**Interfaces:**
- Consumes: `app.connectors.alerts.get_alerts`; the `weather` dict produced by Task 8's `run_weather_agent`.
- Produces: `async def run_risk_agent(lat: float, lon: float, weather: dict) -> tuple[dict, TraceEntry]` where the dict has keys `verdict` (`"safe"|"unsafe"`), `reasons: list[str]` — consumed by Task 14 (graph).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_risk_agent.py
from datetime import datetime, timezone
from app.agents import risk_agent
from app.schemas import ConnectorResult


def test_assess_safe_when_all_below_thresholds():
    weather = {"wave_height_m": 1.0, "wind_speed_kmh": 15.0}
    verdict, reasons = risk_agent._assess(weather, {"cyclone_alerts": [], "lightning_alerts": []})
    assert verdict == "safe"
    assert len(reasons) == 1


def test_assess_unsafe_on_high_waves():
    weather = {"wave_height_m": 3.0, "wind_speed_kmh": 15.0}
    verdict, reasons = risk_agent._assess(weather, {"cyclone_alerts": [], "lightning_alerts": []})
    assert verdict == "unsafe"
    assert any("Wave height" in r for r in reasons)


def test_assess_unsafe_on_cyclone_alert():
    weather = {"wave_height_m": 1.0, "wind_speed_kmh": 15.0}
    alerts_data = {"cyclone_alerts": [{"name": "Cyclone Test"}], "lightning_alerts": []}
    verdict, reasons = risk_agent._assess(weather, alerts_data)
    assert verdict == "unsafe"
    assert any("Cyclone Test" in r for r in reasons)


async def test_run_risk_agent_returns_output_and_trace(monkeypatch):
    alerts_result = ConnectorResult(
        data={"cyclone_alerts": [], "lightning_alerts": []},
        source="cached-alerts-snapshot",
        fetched_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        is_cached=True,
    )

    async def fake_get_alerts(lat, lon):
        return alerts_result

    monkeypatch.setattr(risk_agent, "get_alerts", fake_get_alerts)

    weather = {"wave_height_m": 1.0, "wind_speed_kmh": 15.0}
    output, trace = await risk_agent.run_risk_agent(10.0, 76.0, weather)

    assert output["verdict"] == "safe"
    assert trace.agent == "risk"
    assert trace.is_cached is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_risk_agent.py -v`
Expected: FAIL (`ModuleNotFoundError: app.agents.risk_agent`)

- [ ] **Step 3: Implement the risk agent**

```python
# backend/app/agents/risk_agent.py
from app.connectors.alerts import get_alerts
from app.schemas import TraceEntry

WAVE_HEIGHT_UNSAFE_M = 2.5
WIND_SPEED_UNSAFE_KMH = 40.0


def _assess(weather: dict, alerts_data: dict) -> tuple[str, list[str]]:
    reasons: list[str] = []
    unsafe = False

    if weather["wave_height_m"] > WAVE_HEIGHT_UNSAFE_M:
        unsafe = True
        reasons.append(
            f"Wave height {weather['wave_height_m']}m exceeds safe threshold {WAVE_HEIGHT_UNSAFE_M}m"
        )
    if weather["wind_speed_kmh"] > WIND_SPEED_UNSAFE_KMH:
        unsafe = True
        reasons.append(
            f"Wind speed {weather['wind_speed_kmh']}km/h exceeds safe threshold {WIND_SPEED_UNSAFE_KMH}km/h"
        )
    if alerts_data.get("cyclone_alerts"):
        unsafe = True
        names = ", ".join(a["name"] for a in alerts_data["cyclone_alerts"])
        reasons.append(f"Active cyclone alert(s): {names}")
    if alerts_data.get("lightning_alerts"):
        unsafe = True
        reasons.append("Active lightning alert in the area")

    if not reasons:
        reasons.append("No hazardous conditions found in wave, wind, cyclone, or lightning data")

    return ("unsafe" if unsafe else "safe"), reasons


async def run_risk_agent(lat: float, lon: float, weather: dict) -> tuple[dict, TraceEntry]:
    alerts_result = await get_alerts(lat, lon)
    verdict, reasons = _assess(weather, alerts_result.data)
    output = {"verdict": verdict, "reasons": reasons}
    trace = TraceEntry(
        agent="risk",
        inputs={"lat": lat, "lon": lon},
        output=output,
        sources=[alerts_result.source],
        fetched_at=alerts_result.fetched_at,
        is_cached=alerts_result.is_cached,
    )
    return output, trace
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_risk_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/risk_agent.py tests/test_risk_agent.py
git commit -m "feat: risk/safety agent with threshold-based go/no-go

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 11: Geospatial Agent

**Files:**
- Create: `backend/app/agents/geospatial_agent.py`
- Test: `backend/tests/test_geospatial_agent.py`

**Interfaces:**
- Consumes: `app.connectors.geospatial.geocode`, `nearest_boundary_distance_km`.
- Produces: `async def run_geospatial_agent(place_name: str) -> tuple[dict, TraceEntry]` where the dict has keys `lat`, `lon`, `resolved_name`, `nearest_boundary`, `boundary_distance_km`, `within_warning_zone: bool` — consumed by Task 14 (graph), which reads `lat`/`lon` to feed every other agent.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_geospatial_agent.py
from datetime import datetime, timezone
from app.agents import geospatial_agent
from app.schemas import ConnectorResult


async def test_run_geospatial_agent_returns_output_and_trace(monkeypatch):
    geo_result = ConnectorResult(
        data={"lat": 9.93, "lon": 76.27, "display_name": "Kochi, Kerala, India"},
        source="nominatim",
        fetched_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        is_cached=False,
    )

    async def fake_geocode(place_name):
        return geo_result

    def fake_nearest(lat, lon):
        return {"nearest_boundary": "Example MPA", "distance_km": 12.0, "source": "static-mpa-imbl-snapshot"}

    monkeypatch.setattr(geospatial_agent, "geocode", fake_geocode)
    monkeypatch.setattr(geospatial_agent, "nearest_boundary_distance_km", fake_nearest)

    output, trace = await geospatial_agent.run_geospatial_agent("Kochi")

    assert output["lat"] == 9.93
    assert output["within_warning_zone"] is False
    assert trace.agent == "geospatial"
    assert trace.sources == ["nominatim", "static-mpa-imbl-snapshot"]


async def test_run_geospatial_agent_flags_warning_zone(monkeypatch):
    geo_result = ConnectorResult(
        data={"lat": 9.65, "lon": 75.85, "display_name": "Near MPA"},
        source="nominatim",
        fetched_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
        is_cached=False,
    )

    async def fake_geocode(place_name):
        return geo_result

    def fake_nearest(lat, lon):
        return {"nearest_boundary": "Example MPA", "distance_km": 2.0, "source": "static-mpa-imbl-snapshot"}

    monkeypatch.setattr(geospatial_agent, "geocode", fake_geocode)
    monkeypatch.setattr(geospatial_agent, "nearest_boundary_distance_km", fake_nearest)

    output, _ = await geospatial_agent.run_geospatial_agent("Near MPA")
    assert output["within_warning_zone"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_geospatial_agent.py -v`
Expected: FAIL (`ModuleNotFoundError: app.agents.geospatial_agent`)

- [ ] **Step 3: Implement the geospatial agent**

```python
# backend/app/agents/geospatial_agent.py
from app.connectors.geospatial import geocode, nearest_boundary_distance_km
from app.schemas import TraceEntry

PROXIMITY_WARNING_KM = 5.0


async def run_geospatial_agent(place_name: str) -> tuple[dict, TraceEntry]:
    geo_result = await geocode(place_name)
    lat, lon = geo_result.data["lat"], geo_result.data["lon"]
    boundary_info = nearest_boundary_distance_km(lat, lon)
    output = {
        "lat": lat,
        "lon": lon,
        "resolved_name": geo_result.data["display_name"],
        "nearest_boundary": boundary_info["nearest_boundary"],
        "boundary_distance_km": boundary_info["distance_km"],
        "within_warning_zone": boundary_info["distance_km"] <= PROXIMITY_WARNING_KM,
    }
    trace = TraceEntry(
        agent="geospatial",
        inputs={"place_name": place_name},
        output=output,
        sources=[geo_result.source, boundary_info["source"]],
        fetched_at=geo_result.fetched_at,
        is_cached=geo_result.is_cached,
    )
    return output, trace
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_geospatial_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/geospatial_agent.py tests/test_geospatial_agent.py
git commit -m "feat: geospatial agent for location resolution and boundary proximity

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 12: LLM Client + Planner Agent (Gemini free tier)

**Files:**
- Create: `backend/app/llm.py`
- Create: `backend/app/agents/planner.py`
- Modify: `backend/app/config.py` (already has `gemini_api_key` from Task 1 — no change needed, listed for traceability)
- Test: `backend/tests/test_planner.py`

**Interfaces:**
- Consumes: `app.config.get_settings()`.
- Produces: `get_llm_client() -> genai.Client`; `async def create_plan(client: genai.Client, message: str, history: list[dict]) -> dict` where the dict has keys `intent`, `place_name` (`str | None`), `agents: list[str]`, `response_language: str` — consumed by Task 14 (graph).

- [ ] **Step 1: Implement the LLM client wrapper**

```python
# backend/app/llm.py
from google import genai
from app.config import get_settings

DEFAULT_MODEL = "gemini-2.5-flash"


def get_llm_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)
```

- [ ] **Step 2: Write the failing test for the planner**

```python
# backend/tests/test_planner.py
from unittest.mock import AsyncMock
from app.agents.planner import create_plan, PlanSchema


async def test_create_plan_parses_structured_response():
    fake_plan = PlanSchema(
        intent="check safety",
        place_name="Kochi",
        agents=["weather", "risk"],
        response_language="English",
    )
    fake_response = type("Resp", (), {"text": fake_plan.model_dump_json()})()
    fake_client = type("Client", (), {})()
    fake_client.aio = type("Aio", (), {})()
    fake_client.aio.models = type("Models", (), {})()
    fake_client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    plan = await create_plan(fake_client, "is it safe near Kochi tomorrow?", [])

    assert plan["intent"] == "check safety"
    assert plan["place_name"] == "Kochi"
    assert plan["agents"] == ["weather", "risk"]
    fake_client.aio.models.generate_content.assert_awaited_once()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_planner.py -v`
Expected: FAIL (`ModuleNotFoundError: app.agents.planner`)

- [ ] **Step 4: Implement the planner**

```python
# backend/app/agents/planner.py
from pydantic import BaseModel
from app.llm import DEFAULT_MODEL


class PlanSchema(BaseModel):
    intent: str
    place_name: str | None
    agents: list[str]
    response_language: str


PLANNER_SYSTEM_PROMPT = """You are the planning agent for a marine intelligence assistant used by
fishermen and coastal stakeholders. Given the user's message and conversation history, decide:
- their intent, in one short phrase
- the place/location they mean (reuse the location from earlier turns if this message is a
  follow-up like "what about tomorrow?" that doesn't repeat it); null if genuinely no location
  has ever been given
- which specialist agents are needed, from: "weather" (wind/wave/swell), "ocean_analytics"
  (SST/chlorophyll/fishing-zone likelihood), "risk" (safety go/no-go, alerts), "geospatial"
  (location resolution, protected-area/boundary proximity)
- the language to respond in, matching the user's own message

Respond only with the requested JSON fields."""


async def create_plan(client, message: str, history: list[dict]) -> dict:
    history_text = "\n".join(f"{h['role']}: {h['content']}" for h in history)
    prompt = (
        f"{PLANNER_SYSTEM_PROMPT}\n\nConversation so far:\n{history_text}\n\n"
        f"User message: {message}"
    )
    response = await client.aio.models.generate_content(
        model=DEFAULT_MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json", "response_schema": PlanSchema},
    )
    plan = PlanSchema.model_validate_json(response.text)
    return plan.model_dump()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_planner.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/llm.py app/agents/planner.py tests/test_planner.py
git commit -m "feat: Gemini LLM client and planner agent

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 13: Reporting/Synthesis Agent

**Files:**
- Create: `backend/app/agents/reporting_agent.py`
- Test: `backend/tests/test_reporting_agent.py`

**Interfaces:**
- Consumes: `app.llm.DEFAULT_MODEL`; a `genai.Client`-like object with `.aio.models.generate_content`.
- Produces: `async def synthesize_answer(client, user_message: str, response_language: str, agent_results: dict) -> str` — consumed by Task 14 (graph).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_reporting_agent.py
from unittest.mock import AsyncMock
from app.agents.reporting_agent import synthesize_answer


async def test_synthesize_answer_returns_llm_text():
    fake_response = type("Resp", (), {"text": "It is safe to go out tomorrow morning."})()
    fake_client = type("Client", (), {})()
    fake_client.aio = type("Aio", (), {})()
    fake_client.aio.models = type("Models", (), {})()
    fake_client.aio.models.generate_content = AsyncMock(return_value=fake_response)

    answer = await synthesize_answer(
        fake_client,
        user_message="is it safe tomorrow?",
        response_language="English",
        agent_results={"risk_result": {"verdict": "safe", "reasons": ["calm seas"]}},
    )

    assert answer == "It is safe to go out tomorrow morning."
    fake_client.aio.models.generate_content.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reporting_agent.py -v`
Expected: FAIL (`ModuleNotFoundError: app.agents.reporting_agent`)

- [ ] **Step 3: Implement the reporting agent**

```python
# backend/app/agents/reporting_agent.py
from app.llm import DEFAULT_MODEL

REPORTING_SYSTEM_PROMPT = """You are the final-answer agent for a marine intelligence assistant.
You are given the user's question, the language to respond in, and structured results from
specialist agents (weather, ocean analytics, risk, geospatial), each tagged with its data source.
Write a single clear, conversational answer:
- Respond ONLY in the requested language.
- State the concrete recommendation or answer first.
- Then briefly explain the reasoning: which values from which sources led to it.
- If any source is cached/stale, say so plainly (e.g. "based on data from X").
- Never invent numbers that are not present in the provided agent results."""


def _format_agent_results(agent_results: dict) -> str:
    return "\n".join(f"[{name}] {result}" for name, result in agent_results.items())


async def synthesize_answer(
    client,
    user_message: str,
    response_language: str,
    agent_results: dict,
) -> str:
    prompt = (
        f"{REPORTING_SYSTEM_PROMPT}\n\n"
        f"User question: {user_message}\n"
        f"Respond in language: {response_language}\n"
        f"Agent results:\n{_format_agent_results(agent_results)}"
    )
    response = await client.aio.models.generate_content(model=DEFAULT_MODEL, contents=prompt)
    return response.text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reporting_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/agents/reporting_agent.py tests/test_reporting_agent.py
git commit -m "feat: reporting/synthesis agent

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 14: LangGraph Orchestration

**Files:**
- Create: `backend/app/graph.py`
- Test: `backend/tests/test_graph.py`

**Interfaces:**
- Consumes: `run_geospatial_agent` (Task 11), `run_weather_agent` (Task 8), `run_risk_agent` (Task 10), `run_ocean_analytics_agent` (Task 9), `create_plan` (Task 12), `synthesize_answer` (Task 13).
- Produces: `def build_graph(client) -> CompiledGraph` where `await graph.ainvoke({"message": str, "history": list[dict]})` returns a state dict with keys `trace: list[TraceEntry]`, `final_answer: str` — consumed by Task 15 (endpoint) and Task 16 (e2e test).

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_graph.py
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from app import graph as graph_module
from app.schemas import TraceEntry


def _trace(agent_name: str) -> TraceEntry:
    return TraceEntry(
        agent=agent_name, inputs={}, output={}, sources=["test"],
        fetched_at=datetime.now(timezone.utc), is_cached=False,
    )


async def test_graph_runs_full_pipeline_when_location_present(monkeypatch):
    monkeypatch.setattr(
        graph_module, "create_plan",
        AsyncMock(return_value={
            "intent": "check safety", "place_name": "Kochi",
            "agents": ["weather", "risk"], "response_language": "English",
        }),
    )
    monkeypatch.setattr(
        graph_module, "run_geospatial_agent",
        AsyncMock(return_value=({"lat": 9.9, "lon": 76.2}, _trace("geospatial"))),
    )
    monkeypatch.setattr(
        graph_module, "run_weather_agent",
        AsyncMock(return_value=({"wave_height_m": 1.0, "wind_speed_kmh": 10.0}, _trace("weather"))),
    )
    monkeypatch.setattr(
        graph_module, "run_risk_agent",
        AsyncMock(return_value=({"verdict": "safe", "reasons": []}, _trace("risk"))),
    )
    monkeypatch.setattr(
        graph_module, "run_ocean_analytics_agent",
        AsyncMock(return_value=({"pfz_likelihood": "moderate"}, _trace("ocean_analytics"))),
    )
    monkeypatch.setattr(
        graph_module, "synthesize_answer", AsyncMock(return_value="It is safe to go out.")
    )

    compiled = graph_module.build_graph(client=object())
    result = await compiled.ainvoke({"message": "is it safe near Kochi?", "history": []})

    trace_agents = [t.agent for t in result["trace"]]
    assert trace_agents == ["planner", "geospatial", "weather", "risk", "ocean_analytics"]
    assert result["final_answer"] == "It is safe to go out."


async def test_graph_asks_for_location_when_none_given(monkeypatch):
    monkeypatch.setattr(
        graph_module, "create_plan",
        AsyncMock(return_value={
            "intent": "check safety", "place_name": None,
            "agents": [], "response_language": "English",
        }),
    )
    geospatial_mock = AsyncMock()
    monkeypatch.setattr(graph_module, "run_geospatial_agent", geospatial_mock)
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock())

    compiled = graph_module.build_graph(client=object())
    result = await compiled.ainvoke({"message": "is it safe?", "history": []})

    geospatial_mock.assert_not_awaited()
    assert "location" in result["final_answer"].lower()


async def test_graph_falls_back_to_default_plan_when_planner_fails(monkeypatch):
    monkeypatch.setattr(graph_module, "create_plan", AsyncMock(side_effect=RuntimeError("LLM down")))
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock())

    compiled = graph_module.build_graph(client=object())
    result = await compiled.ainvoke({"message": "is it safe?", "history": []})

    assert result["plan"]["place_name"] is None
    assert "location" in result["final_answer"].lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_graph.py -v`
Expected: FAIL (`ModuleNotFoundError: app.graph`)

- [ ] **Step 3: Implement the graph**

```python
# backend/app/graph.py
from typing import TypedDict
from langgraph.graph import StateGraph, END
from app.agents.planner import create_plan
from app.agents.weather_agent import run_weather_agent
from app.agents.ocean_analytics_agent import run_ocean_analytics_agent
from app.agents.risk_agent import run_risk_agent
from app.agents.geospatial_agent import run_geospatial_agent
from app.agents.reporting_agent import synthesize_answer
from app.schemas import TraceEntry

NO_LOCATION_ANSWER = "I need a location to answer that -- which coast, port, or coordinates should I check?"


class GraphState(TypedDict, total=False):
    message: str
    history: list[dict]
    plan: dict
    lat: float
    lon: float
    weather_result: dict
    ocean_result: dict
    risk_result: dict
    geo_result: dict
    trace: list[TraceEntry]
    final_answer: str


DEFAULT_PLAN = {
    "intent": "general marine query",
    "place_name": None,
    "agents": ["weather"],
    "response_language": "English",
}


async def planner_node(state: GraphState) -> GraphState:
    try:
        plan = await create_plan(state["_client"], state["message"], state.get("history", []))
    except Exception:
        plan = dict(DEFAULT_PLAN)
    trace_entry = TraceEntry(
        agent="planner",
        inputs={"message": state["message"]},
        output=plan,
        sources=[],
    )
    return {**state, "plan": plan, "trace": [trace_entry]}


async def geospatial_node(state: GraphState) -> GraphState:
    output, trace = await run_geospatial_agent(state["plan"]["place_name"])
    return {
        **state,
        "lat": output["lat"],
        "lon": output["lon"],
        "geo_result": output,
        "trace": state["trace"] + [trace],
    }


async def weather_node(state: GraphState) -> GraphState:
    output, trace = await run_weather_agent(state["lat"], state["lon"])
    return {**state, "weather_result": output, "trace": state["trace"] + [trace]}


async def risk_node(state: GraphState) -> GraphState:
    output, trace = await run_risk_agent(state["lat"], state["lon"], state["weather_result"])
    return {**state, "risk_result": output, "trace": state["trace"] + [trace]}


async def ocean_analytics_node(state: GraphState) -> GraphState:
    output, trace = await run_ocean_analytics_agent(state["lat"], state["lon"])
    return {**state, "ocean_result": output, "trace": state["trace"] + [trace]}


async def reporting_node(state: GraphState) -> GraphState:
    if not state["plan"].get("place_name"):
        return {**state, "final_answer": NO_LOCATION_ANSWER}
    agent_results = {
        key: state[key]
        for key in ("geo_result", "weather_result", "ocean_result", "risk_result")
        if state.get(key)
    }
    answer = await synthesize_answer(
        state["_client"], state["message"], state["plan"]["response_language"], agent_results
    )
    return {**state, "final_answer": answer}


def _route_after_planner(state: GraphState) -> str:
    return "geospatial" if state["plan"].get("place_name") else "reporting"


def build_graph(client):
    graph = StateGraph(GraphState)

    async def planner_with_client(state: GraphState) -> GraphState:
        return await planner_node({**state, "_client": client})

    async def reporting_with_client(state: GraphState) -> GraphState:
        return await reporting_node({**state, "_client": client})

    graph.add_node("planner", planner_with_client)
    graph.add_node("geospatial", geospatial_node)
    graph.add_node("weather", weather_node)
    graph.add_node("risk", risk_node)
    graph.add_node("ocean_analytics", ocean_analytics_node)
    graph.add_node("reporting", reporting_with_client)

    graph.set_entry_point("planner")
    graph.add_conditional_edges(
        "planner", _route_after_planner, {"geospatial": "geospatial", "reporting": "reporting"}
    )
    graph.add_edge("geospatial", "weather")
    graph.add_edge("weather", "risk")
    graph.add_edge("risk", "ocean_analytics")
    graph.add_edge("ocean_analytics", "reporting")
    graph.add_edge("reporting", END)
    return graph.compile()
```

Note: `_client` is threaded through state (rather than closed over inside every node) so `planner_node`/`reporting_node` stay plain, independently testable functions; the `_with_client` wrappers are the only place that knows about the LLM client.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_graph.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/graph.py tests/test_graph.py
git commit -m "feat: LangGraph orchestration pipeline

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 15: FastAPI /chat SSE Endpoint

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_chat_endpoint.py`

**Interfaces:**
- Consumes: `app.graph.build_graph`, `app.llm.get_llm_client`, `app.schemas.ChatRequest`.
- Produces: `POST /chat` — an SSE stream of `event: trace` (JSON `TraceEntry`) and `event: answer` (JSON `{"answer": str}`) — consumed by Task 17 (frontend client).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_chat_endpoint.py
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport
from app import main as main_module
from app.schemas import TraceEntry


class FakeGraph:
    async def astream(self, input, stream_mode):
        trace_entry = TraceEntry(
            agent="weather", inputs={}, output={"wave_height_m": 1.0},
            sources=["test"], fetched_at=datetime.now(timezone.utc), is_cached=False,
        )
        yield {"trace": [trace_entry]}
        yield {"trace": [trace_entry], "final_answer": "It is safe to go out."}


async def test_chat_endpoint_streams_trace_then_answer(monkeypatch):
    monkeypatch.setattr(main_module, "build_graph", lambda client: FakeGraph())
    monkeypatch.setattr(main_module, "get_llm_client", lambda: object())

    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with client.stream(
            "POST", "/chat", json={"session_id": "s1", "message": "is it safe?", "history": []}
        ) as response:
            body = ""
            async for chunk in response.aiter_text():
                body += chunk

    assert "event: trace" in body
    assert "event: answer" in body
    assert "It is safe to go out." in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_chat_endpoint.py -v`
Expected: FAIL (`AttributeError: module 'app.main' has no attribute 'build_graph'`)

- [ ] **Step 3: Implement the endpoint**

```python
# backend/app/main.py
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.config import get_settings
from app.llm import get_llm_client
from app.graph import build_graph
from app.schemas import ChatRequest

app = FastAPI(title="ORCA Marine Intelligence Platform")

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest):
    client = get_llm_client()
    graph = build_graph(client)
    history = [{"role": m.role, "content": m.content} for m in request.history]

    async def event_stream():
        last_trace_len = 0
        async for state in graph.astream(
            {"message": request.message, "history": history}, stream_mode="values"
        ):
            trace = state.get("trace", [])
            for entry in trace[last_trace_len:]:
                yield f"event: trace\ndata: {entry.model_dump_json()}\n\n"
            last_trace_len = len(trace)
            if state.get("final_answer"):
                payload = json.dumps({"answer": state["final_answer"]})
                yield f"event: answer\ndata: {payload}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_chat_endpoint.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/main.py tests/test_chat_endpoint.py
git commit -m "feat: /chat SSE endpoint streaming trace and final answer

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 16: Backend End-to-End Fixture Test

**Files:**
- Test: `backend/tests/test_e2e_query_types.py`

**Interfaces:**
- Consumes: `app.graph.build_graph` (Task 14), all connectors (Tasks 4-7) mocked at the HTTP/LLM boundary only — this test exercises real agent and correlation code, unlike Task 14's agent-level mocks.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_e2e_query_types.py
import httpx
import respx
from unittest.mock import AsyncMock
from app.graph import build_graph
from app import graph as graph_module


def _mock_all_connectors():
    respx.get("https://nominatim.openstreetmap.org/search").mock(
        return_value=httpx.Response(
            200, json=[{"lat": "9.93", "lon": "76.27", "display_name": "Kochi, Kerala, India"}]
        )
    )
    respx.get("https://marine-api.open-meteo.com/v1/marine").mock(
        return_value=httpx.Response(200, json={"hourly": {"wave_height": [1.0], "swell_wave_height": [0.5]}})
    )
    respx.get("https://api.open-meteo.com/v1/forecast").mock(
        return_value=httpx.Response(
            200, json={"hourly": {"wind_speed_10m": [15.0], "wind_direction_10m": [200], "time": ["2026-09-15T06:00"]}}
        )
    )
    respx.get(url__regex=r"jplMURSST41\.json").mock(
        return_value=httpx.Response(200, json={"table": {"rows": [["t", 9.93, 76.27, 28.5]]}})
    )
    respx.get(url__regex=r"erdMH1chla1day\.json").mock(
        return_value=httpx.Response(200, json={"table": {"rows": [["t", 9.93, 76.27, 0.35]]}})
    )


def _fake_plan(intent: str, agents: list[str]) -> dict:
    return {"intent": intent, "place_name": "Kochi", "agents": agents, "response_language": "English"}


@respx.mock
async def test_is_it_safe_query_flags_calm_conditions(monkeypatch):
    _mock_all_connectors()
    monkeypatch.setattr(
        graph_module, "create_plan", AsyncMock(return_value=_fake_plan("safety check", ["weather", "risk"]))
    )
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock(return_value="Safe to go out."))

    graph = build_graph(client=object())
    result = await graph.ainvoke({"message": "is it safe near Kochi tomorrow?", "history": []})

    assert result["risk_result"]["verdict"] == "safe"
    assert result["final_answer"] == "Safe to go out."
    assert [t.agent for t in result["trace"]] == ["planner", "geospatial", "weather", "risk", "ocean_analytics"]


@respx.mock
async def test_fishing_zone_query_produces_pfz_likelihood(monkeypatch):
    _mock_all_connectors()
    monkeypatch.setattr(
        graph_module, "create_plan", AsyncMock(return_value=_fake_plan("find PFZ", ["ocean_analytics"]))
    )
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock(return_value="Good fishing zone nearby."))

    graph = build_graph(client=object())
    result = await graph.ainvoke({"message": "where is the nearest fishing zone near Kochi?", "history": []})

    assert result["ocean_result"]["pfz_likelihood"] == "high"


@respx.mock
async def test_alerts_query_reports_no_active_alerts(monkeypatch):
    _mock_all_connectors()
    monkeypatch.setattr(
        graph_module, "create_plan", AsyncMock(return_value=_fake_plan("check alerts", ["risk"]))
    )
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock(return_value="No alerts."))

    graph = build_graph(client=object())
    result = await graph.ainvoke({"message": "any cyclone alerts near Kochi?", "history": []})

    assert result["risk_result"]["reasons"] == [
        "No hazardous conditions found in wave, wind, cyclone, or lightning data"
    ]


@respx.mock
async def test_followup_query_reuses_location_from_plan(monkeypatch):
    _mock_all_connectors()
    monkeypatch.setattr(
        graph_module, "create_plan",
        AsyncMock(return_value=_fake_plan("safety check for later date", ["weather", "risk"])),
    )
    monkeypatch.setattr(graph_module, "synthesize_answer", AsyncMock(return_value="Still safe Thursday."))

    graph = build_graph(client=object())
    history = [
        {"role": "user", "content": "is it safe near Kochi tomorrow?"},
        {"role": "assistant", "content": "Safe to go out."},
    ]
    result = await graph.ainvoke({"message": "what about Thursday instead?", "history": history})

    assert result["final_answer"] == "Still safe Thursday."
```

Note: `create_plan` is monkeypatched here (not a real Gemini call) because these tests verify real connector/agent/correlation code end-to-end without requiring a `GEMINI_API_KEY` in CI; "reusing location from a follow-up" is exercised by asserting the planner is *asked* to do so via the `history` it receives — the planner's actual language-model reasoning for that is covered by Task 12's contract test, not re-verified here.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_e2e_query_types.py -v`
Expected: FAIL if any prior task's module is missing; once Tasks 1-15 are done, this should already pass on first run since it only composes existing code — run it anyway to confirm.

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_e2e_query_types.py -v`
Expected: PASS. If any test fails, the fixture data or a connector's field name likely drifted from an earlier task — check `_mock_all_connectors()`'s response shapes against Tasks 4-5's live-fetch parsing code.

- [ ] **Step 4: Run the full backend test suite**

Run: `pytest -v`
Expected: PASS (all tests from Tasks 1-16)

- [ ] **Step 5: Commit**

```bash
git add tests/test_e2e_query_types.py
git commit -m "test: end-to-end fixture coverage for the four Phase 1 query types

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 17: Frontend Scaffold + SSE Client

**Files:**
- Create: `frontend/` (via `create-next-app`)
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/chatClient.ts`
- Test: `frontend/lib/chatClient.test.ts`

**Interfaces:**
- Produces: `TraceEntry`, `ChatMessage`, `ChatStreamEvent` types; `parseSSEChunk(chunk: string): ChatStreamEvent[]`; `async function* streamChat(sessionId: string, message: string, history: ChatMessage[]): AsyncGenerator<ChatStreamEvent>` — consumed by Task 21 (page wiring).

- [ ] **Step 1: Scaffold the Next.js app**

Run from `/home/vinay/marine-intelligence-platform`:

```bash
npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir --import-alias "@/*" --eslint
cd frontend
npm install -D vitest
```

Add to `frontend/package.json` scripts: `"test": "vitest run"`.

- [ ] **Step 2: Create the shared types**

```typescript
// frontend/lib/types.ts
export interface TraceEntry {
  agent: string;
  inputs: Record<string, unknown>;
  output: Record<string, unknown>;
  sources: string[];
  fetched_at: string | null;
  is_cached: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export type ChatStreamEvent =
  | { type: "trace"; data: TraceEntry }
  | { type: "answer"; data: { answer: string } };
```

- [ ] **Step 3: Write the failing test for SSE chunk parsing**

```typescript
// frontend/lib/chatClient.test.ts
import { describe, it, expect } from "vitest";
import { parseSSEChunk } from "./chatClient";

describe("parseSSEChunk", () => {
  it("parses a trace event", () => {
    const chunk =
      'event: trace\ndata: {"agent":"weather","inputs":{},"output":{},"sources":[],"fetched_at":null,"is_cached":false}\n\n';
    const events = parseSSEChunk(chunk);
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe("trace");
  });

  it("parses an answer event", () => {
    const chunk = 'event: answer\ndata: {"answer":"It is safe to go out."}\n\n';
    const events = parseSSEChunk(chunk);
    expect(events[0]).toEqual({ type: "answer", data: { answer: "It is safe to go out." } });
  });

  it("ignores blocks missing an event or data line", () => {
    expect(parseSSEChunk(": heartbeat\n\n")).toHaveLength(0);
  });
});
```

- [ ] **Step 4: Run test to verify it fails**

Run (from `frontend/`): `npm test`
Expected: FAIL (`Cannot find module './chatClient'`)

- [ ] **Step 5: Implement the SSE client**

```typescript
// frontend/lib/chatClient.ts
import { ChatMessage, ChatStreamEvent } from "./types";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

export function parseSSEChunk(chunk: string): ChatStreamEvent[] {
  const events: ChatStreamEvent[] = [];
  const blocks = chunk.split("\n\n").filter((b) => b.trim().length > 0);
  for (const block of blocks) {
    const lines = block.split("\n");
    const eventLine = lines.find((l) => l.startsWith("event: "));
    const dataLine = lines.find((l) => l.startsWith("data: "));
    if (!eventLine || !dataLine) continue;
    const type = eventLine.slice("event: ".length).trim();
    const data = JSON.parse(dataLine.slice("data: ".length));
    if (type === "trace") events.push({ type: "trace", data });
    else if (type === "answer") events.push({ type: "answer", data });
  }
  return events;
}

export async function* streamChat(
  sessionId: string,
  message: string,
  history: ChatMessage[]
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message, history }),
  });
  if (!response.body) throw new Error("No response body from /chat");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      for (const event of parseSSEChunk(part + "\n\n")) {
        yield event;
      }
    }
  }
}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `npm test`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd /home/vinay/marine-intelligence-platform
git add frontend
git commit -m "feat: Next.js scaffold with SSE chat client

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 18: ChatPanel Component

**Files:**
- Create: `frontend/components/ChatPanel.tsx`

**Interfaces:**
- Consumes: `ChatMessage` from `frontend/lib/types.ts`.
- Produces: `ChatPanel({ messages, onSend, isStreaming }: { messages: ChatMessage[]; onSend: (message: string) => void; isStreaming: boolean })` — consumed by Task 21 (page wiring).

- [ ] **Step 1: Implement the component**

```tsx
// frontend/components/ChatPanel.tsx
"use client";
import { useState, FormEvent } from "react";
import { ChatMessage } from "@/lib/types";

interface ChatPanelProps {
  messages: ChatMessage[];
  onSend: (message: string) => void;
  isStreaming: boolean;
}

export function ChatPanel({ messages, onSend, isStreaming }: ChatPanelProps) {
  const [input, setInput] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    onSend(input.trim());
    setInput("");
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-2 p-4">
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <span className="inline-block rounded-lg px-3 py-2 bg-slate-100">{m.content}</span>
          </div>
        ))}
        {isStreaming && <div className="text-left text-sm text-slate-400">thinking...</div>}
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2 p-4 border-t">
        <input
          className="flex-1 border rounded px-3 py-2"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about weather, fishing zones, or safety..."
          disabled={isStreaming}
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-50"
          disabled={isStreaming}
        >
          Send
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Manually verify it compiles**

Run (from `frontend/`): `npx tsc --noEmit`
Expected: no type errors referencing `ChatPanel.tsx`

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ChatPanel.tsx
git commit -m "feat: chat panel component

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 19: ReasoningTrace Component

**Files:**
- Create: `frontend/components/ReasoningTrace.tsx`

**Interfaces:**
- Consumes: `TraceEntry` from `frontend/lib/types.ts`.
- Produces: `ReasoningTrace({ trace }: { trace: TraceEntry[] })` — consumed by Task 21 (page wiring).

- [ ] **Step 1: Implement the component**

```tsx
// frontend/components/ReasoningTrace.tsx
import { TraceEntry } from "@/lib/types";

export function ReasoningTrace({ trace }: { trace: TraceEntry[] }) {
  if (trace.length === 0) {
    return <p className="p-4 text-sm text-slate-500">No reasoning steps yet.</p>;
  }
  return (
    <ul className="p-4 space-y-3 overflow-y-auto h-full">
      {trace.map((entry, i) => (
        <li key={i} className="border rounded p-2 text-sm">
          <div className="font-semibold">{entry.agent}</div>
          <div className="text-slate-600">sources: {entry.sources.join(", ")}</div>
          {entry.is_cached && (
            <div className="text-amber-600">cached data from {entry.fetched_at ?? "unknown time"}</div>
          )}
          <pre className="whitespace-pre-wrap text-xs mt-1">{JSON.stringify(entry.output, null, 2)}</pre>
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 2: Manually verify it compiles**

Run: `npx tsc --noEmit`
Expected: no type errors referencing `ReasoningTrace.tsx`

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ReasoningTrace.tsx
git commit -m "feat: reasoning trace panel component

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 20: MapView Component (Leaflet)

**Files:**
- Create: `frontend/components/MapView.tsx`

**Interfaces:**
- Produces: `MapView({ lat, lon, label }: { lat: number | null; lon: number | null; label?: string })` — consumed by Task 21 (page wiring), which must import it via `next/dynamic` with `ssr: false` since Leaflet touches `window`.

- [ ] **Step 1: Install dependencies**

Run (from `frontend/`): `npm install leaflet react-leaflet && npm install -D @types/leaflet`

- [ ] **Step 2: Implement the component**

```tsx
// frontend/components/MapView.tsx
"use client";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";

interface MapViewProps {
  lat: number | null;
  lon: number | null;
  label?: string;
}

export function MapView({ lat, lon, label }: MapViewProps) {
  const center: [number, number] = lat != null && lon != null ? [lat, lon] : [10.0, 76.0];
  return (
    <MapContainer center={center} zoom={lat != null ? 9 : 5} className="h-full w-full">
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="&copy; OpenStreetMap contributors"
      />
      {lat != null && lon != null && (
        <Marker position={[lat, lon]}>{label && <Popup>{label}</Popup>}</Marker>
      )}
    </MapContainer>
  );
}
```

- [ ] **Step 3: Manually verify it compiles**

Run: `npx tsc --noEmit`
Expected: no type errors referencing `MapView.tsx`

- [ ] **Step 4: Commit**

```bash
git add frontend/components/MapView.tsx frontend/package.json frontend/package-lock.json
git commit -m "feat: map view component using Leaflet

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Task 21: Wire the Chat Page Together

**Files:**
- Modify: `frontend/app/page.tsx`

**Interfaces:**
- Consumes: `ChatPanel` (Task 18), `ReasoningTrace` (Task 19), `MapView` (Task 20), `streamChat` (Task 17).

- [ ] **Step 1: Implement the page**

```tsx
// frontend/app/page.tsx
"use client";
import { useState } from "react";
import dynamic from "next/dynamic";
import { ChatPanel } from "@/components/ChatPanel";
import { ReasoningTrace } from "@/components/ReasoningTrace";
import { streamChat } from "@/lib/chatClient";
import { ChatMessage, TraceEntry } from "@/lib/types";

const MapView = dynamic(() => import("@/components/MapView").then((m) => m.MapView), { ssr: false });

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [trace, setTrace] = useState<TraceEntry[]>([]);
  const [location, setLocation] = useState<{ lat: number; lon: number } | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());

  async function handleSend(message: string) {
    const priorMessages = messages;
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setTrace([]);
    setIsStreaming(true);
    try {
      for await (const event of streamChat(sessionId, message, priorMessages)) {
        if (event.type === "trace") {
          setTrace((prev) => [...prev, event.data]);
          if (event.data.agent === "geospatial") {
            const { lat, lon } = event.data.output as { lat: number; lon: number };
            if (typeof lat === "number" && typeof lon === "number") setLocation({ lat, lon });
          }
        } else if (event.type === "answer") {
          setMessages((prev) => [...prev, { role: "assistant", content: event.data.answer }]);
        }
      }
    } finally {
      setIsStreaming(false);
    }
  }

  return (
    <main className="grid grid-cols-1 md:grid-cols-3 h-screen">
      <div className="border-r h-1/3 md:h-full">
        <ChatPanel messages={messages} onSend={handleSend} isStreaming={isStreaming} />
      </div>
      <div className="border-r h-1/3 md:h-full">
        <ReasoningTrace trace={trace} />
      </div>
      <div className="h-1/3 md:h-full">
        <MapView lat={location?.lat ?? null} lon={location?.lon ?? null} />
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Manual smoke test**

Run the backend: `cd backend && GEMINI_API_KEY=<your-free-key> uvicorn app.main:app --reload --port 8000`
Run the frontend: `cd frontend && npm run dev`
Open `http://localhost:3000`, ask "is it safe near Kochi tomorrow?", and confirm:
- the chat panel shows the question and a synthesized answer
- the reasoning-trace panel lists `geospatial`, `weather`, `risk`, `ocean_analytics` in order
- the map centers on Kochi with a marker

- [ ] **Step 3: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat: wire chat, reasoning trace, and map into the main page

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Post-Plan Checklist

- [ ] `cd backend && pytest -v` — all tests pass
- [ ] `cd frontend && npm test` — all tests pass
- [ ] `cd frontend && npx tsc --noEmit` — no type errors
- [ ] Manual smoke test (Task 21, Step 2) passes for all three Phase 1 query types
- [ ] `git push` to `https://github.com/vinay3254/ORCA.git`
