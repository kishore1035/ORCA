# Marine Intelligence Platform — Phase 1: Core Agentic MVP

Status: Draft for review
Date: 2026-09-15
Author: Vinay (with Claude)

## 1. Problem & Scope

The full project brief describes an agentic AI platform that turns fragmented
satellite/oceanographic/weather data into safe, explainable, conversational
answers for fishermen, researchers, coastal authorities, and maritime
operators, in the user's own language.

That brief spans at least eight independent subsystems: multi-agent
orchestration, heterogeneous data ingestion, ocean/weather analytics,
geospatial reasoning, risk assessment + geofencing, route optimization,
multilingual/voice/SMS interaction, and visualization/reporting. Building all
of them shallowly produces a system of stubs, not a platform. This spec
covers **Phase 1 only**: a working agentic core that answers a handful of the
platform's top query types end-to-end, with real correlation logic and a
visible reasoning trace — the "working, well-reasoned core" the brief itself
asks to prioritize.

### Explicitly out of scope for Phase 1 (deferred to later phases)

- Route optimization / vessel navigation agent
- Live geofencing against real-time MPA/IMBL feeds (Phase 1 uses a static
  boundary snapshot)
- Voice, SMS, and IVR channels
- Proactive push alerting (the brief's "flag hazards before the user asks")
- Multi-user accounts, auth, and persistent conversation history (Postgres)
- Any data source without a free/open API — these are represented via
  cached/historical snapshots behind the same connector interface a live
  integration would use, so Phase 2 can swap in real feeds without
  reworking callers

### Query types Phase 1 must answer end-to-end, with real reasoning

1. "Is it safe to go out [tomorrow / this morning] near `<location>`?"
2. "Where is the nearest good fishing zone [near `<location>`]?"
3. "Are there any cyclone/lightning alerts near `<location>`?"
4. Multi-turn refinement of any of the above (e.g. "what about Thursday
   instead?", "what if I go further north?") without the user repeating
   context.

## 2. Architecture

```
┌─────────────────────────────┐        SSE stream        ┌───────────────────────────────┐
│  Next.js frontend (TS)      │◄─────────────────────────┤  FastAPI backend (Python)     │
│  - chat panel               │───────────────────────────►│  POST /chat                   │
│  - map (Mapbox GL/Leaflet)  │   user message + session   │  - LangGraph orchestration    │
│  - reasoning trace panel    │     state (turn history)   │    graph                      │
└─────────────────────────────┘                             │  - connectors/ data layer      │
                                                              └───────────────────────────────┘
```

- **Frontend**: Next.js App Router, TypeScript. Three panels: chat,
  map (renders points/zones/alerts the backend returns as GeoJSON), and a
  collapsible reasoning-trace list (plan → agents invoked → sources cited).
- **Backend**: FastAPI, single `POST /chat` endpoint, Server-Sent Events
  streaming so the trace and final answer can render incrementally.
- **Orchestration**: LangGraph. A **Planner node** reads the user message +
  conversation state, produces a subtask plan (which agents to call, in what
  order/parallelism), and the graph executes it. Chosen over a hand-rolled
  orchestrator (more plumbing to rebuild: state, streaming, retries) and over
  CrewAI/AutoGen (more opaque, harder to expose a faithful reasoning trace,
  which the brief requires).
- **State/session**: no database in Phase 1. The frontend holds and resends
  the running conversation state each turn (or the backend keeps it
  in-process keyed by a session id for the life of the process). Flagged as a
  Phase 2 item once persistent history across restarts/devices matters.

## 3. Agents

| Agent | Responsibility | Data sources (Phase 1) |
|---|---|---|
| **Planner** | Classify intent, decompose into a subtask DAG, route to specialists, hold multi-turn context | — (LLM reasoning only) |
| **Weather Agent** | Wind, wave height, swell, forecast | Open-Meteo Marine API (free, no key) |
| **Ocean Analytics Agent** | SST + chlorophyll retrieval and correlation into a PFZ-likelihood score, with thresholds shown | Copernicus Marine (SST, free w/ registration), NASA Ocean Color (chlorophyll, free w/ Earthdata login) |
| **Risk/Safety Agent** | Combine wave/wind + cyclone/lightning alerts into a go/no-go with cited thresholds | Weather Agent output + cached cyclone/lightning snapshot (no free live feed identified for IMD/INCOIS; connector is pluggable for Phase 2) |
| **Geospatial Agent** | Resolve place names → coordinates; proximity check against MPA/international-boundary layer | Static GeoJSON snapshot (marine protected areas / IMBL) |
| **Reporting/Synthesis Agent** | Merge specialist outputs + trace into one NL answer, in the user's detected language, with citations | Claude (detect + translate + synthesize inline; no separate NLP pipeline) |

Every agent call is recorded in a trace list: `{agent, inputs, output,
sources, fetched_at, is_cached}`. This list is returned to the frontend
alongside the final answer — this *is* the "make the agentic behavior
demonstrable" requirement from the brief, not an add-on.

## 4. Data Ingestion Layer

A `connectors/` package, one module per external source. Each connector
returns a normalized object:

```python
@dataclass
class ConnectorResult:
    data: Any
    source: str          # e.g. "open-meteo-marine"
    fetched_at: datetime
    is_cached: bool       # True if served from committed snapshot, not live
```

Rules:
- A live fetch failure (timeout, quota, auth) falls back to a committed
  historical snapshot for that source — the system **never fabricates**
  values and always surfaces `is_cached=True` + the snapshot's real
  timestamp to the Reporting Agent, which must disclose staleness in the
  answer when relevant (e.g. "based on data from 6 hours ago").
- Adding a new source later (e.g. a real INCOIS/IMD feed) means adding one
  connector module with this same interface — no changes to agents or the
  orchestration graph.

## 5. Error Handling & Reliability

- Connector failure → cached fallback (above), never a hard error surfaced
  to the user unless *no* data (live or cached) exists for that source, in
  which case the Reporting Agent says so explicitly rather than guessing.
- Planner failure to produce a valid plan → fall back to a single-agent
  best-effort (e.g. treat as a generic weather query) rather than erroring
  the whole turn.
- All external HTTP calls have timeouts and are retried once before falling
  back to cache.

## 6. Testing Strategy

- **Connectors**: pytest with mocked HTTP responses — verify normalization,
  cache fallback behavior, and staleness flagging.
- **Correlation logic**: pytest against fixture SST/chlorophyll grids with
  known expected PFZ-likelihood outputs (does the Ocean Analytics Agent
  flag the right zones at the right thresholds).
- **End-to-end**: a small scripted set of the four Phase 1 query types run
  against the LangGraph graph with fixture connector data, asserting the
  trace contains the expected agents and the answer contains the expected
  key facts (not exact-string matching, since it's LLM-generated).

## 7. Open Items for Phase 2 (explicitly deferred, not forgotten)

- Real INCOIS/IMD/cyclone-alert live feeds once access is confirmed (alerts connector still serves a static, always-empty cached snapshot)
- Route optimization agent
- Live geofencing feed against a real MPA/IMBL dataset (still one static example polygon; the proximity check and warning message are real, the boundary data is not)
- Voice/SMS/IVR channels
- Proactive/push alerting (hazard/geofence warnings are surfaced only when the user asks, not pushed ahead of a query)
- Persistent multi-user history (Postgres)

**Added post-MVP, no longer deferred (2026-09-15):** real historical SST trend (7-day ERDDAP time series) feeding a basic warming/cooling/stable signal into the ocean-analytics reasoning and the reporting answer; a deterministic geofence warning surfaced prominently in the answer whenever a query resolves near the static MPA snapshot; a real chart (SST trend sparkline) in the reasoning-trace panel instead of raw JSON only.
