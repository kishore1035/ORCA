# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project State

This repo currently contains **planning documents only** — no implementation exists yet. Before writing or modifying any code here, read, in order:

1. `docs/superpowers/specs/2026-09-15-core-agentic-mvp-design.md` — the design spec (what to build and why, what's explicitly out of scope for Phase 1).
2. `docs/superpowers/plans/2026-09-15-core-agentic-mvp.md` — the task-by-task implementation plan (exact file paths, interfaces, test-driven steps, commit points). This is the authoritative source for file structure, module boundaries, and function signatures — don't improvise a different structure without checking it first.

If asked to continue implementation, follow the plan's tasks in order using the `superpowers:subagent-driven-development` or `superpowers:executing-plans` skill, as the plan's header specifies.

## What's Being Built

ORCA: an agentic marine-intelligence assistant (Phase 1 of a larger platform). A LangGraph pipeline of specialist agents (planner → geospatial → weather → risk → ocean_analytics → reporting) answers three query types end-to-end — "is it safe to go out", "where's the nearest fishing zone", "any cyclone/lightning alerts" — with real correlation logic and a visible reasoning trace, backed by free/no-cost external data sources only.

## Architecture (once implemented, per the plan)

**Monorepo layout:** `backend/` (Python/FastAPI/LangGraph) and `frontend/` (Next.js/TypeScript), each with their own dependency and test tooling.

**Backend pipeline (`backend/app/graph.py`):** a fixed LangGraph sequence, not dynamic fan-out:
`planner → geospatial → weather → risk → ocean_analytics → reporting → END`, with one conditional branch — if the planner can't resolve a location, the graph short-circuits straight to `reporting`, which asks the user for one. Every node appends a `TraceEntry` to `state["trace"]`; this trace is streamed to the frontend and *is* the "make agentic reasoning visible" requirement, not optional logging.

**Connector contract (`backend/app/connectors/`):** every external data source (weather, SST, chlorophyll, alerts, geocoding) is one module implementing the same shape — return a `ConnectorResult{data, source, fetched_at, is_cached}` via the shared `fetch_with_fallback()` helper in `connectors/base.py`, which retries a live fetch once, then falls back to a committed snapshot file in `backend/data/snapshots/`. **A connector must never fabricate data** — no live source, no cache miss is architecturally impossible because every connector ships its own snapshot. New data sources plug in by adding one module with this same interface; agents and the graph never change.

**Agents (`backend/app/agents/`)** are thin: each wraps one or more connectors, adds real domain logic (threshold checks, correlation scoring), and returns `(output_dict, TraceEntry)`. The only two agents that call an LLM are `planner.py` (structured-output intent/plan extraction) and `reporting_agent.py` (final NL synthesis) — both via `app/llm.py`.

**LLM constraint:** Google Gemini free tier (`gemini-3.6-flash` via `google-genai`, `GEMINI_API_KEY`) — no paid API of any kind anywhere in this project. This is a deliberate substitution for whatever the original spec assumed; don't reintroduce Anthropic/OpenAI/other paid LLM calls. (Note: the original Phase 1 implementation used `gemini-2.5-flash`, which Google deprecated for new API keys; updated 2026-09-15.)

**Other deliberate deviations from a naive reading of the spec** (see the plan's "Global Constraints" section for the full list): SST/chlorophyll come from NOAA ERDDAP (`jplMURSST41`, `erdMH1chla1day` — free, no registration) rather than Copernicus/NASA; the map uses Leaflet + OpenStreetMap tiles (no API key) rather than Mapbox. No database in Phase 1 — the frontend resends conversation history each turn.

**Frontend (`frontend/`):** the backend's `/chat` endpoint streams Server-Sent Events (`event: trace`, `event: answer`) over a POST request — the native `EventSource` API doesn't support POST, so the client (`frontend/lib/chatClient.ts`) hand-parses the stream via `fetch` + `ReadableStream`. `MapView` (Leaflet) must be loaded via `next/dynamic` with `ssr: false` since Leaflet touches `window`.

## Commands (once Phase 1 is implemented per the plan)

Backend (from `backend/`):
- `pytest -v` — run all tests; `pytest tests/test_<name>.py -v` for a single file
- `uvicorn app.main:app --reload --port 8000` — run the dev server (requires `GEMINI_API_KEY` env var)

Frontend (from `frontend/`):
- `npm test` — run Vitest unit tests
- `npx tsc --noEmit` — type-check
- `npm run dev` — run the dev server (expects backend at `http://localhost:8000`, override via `NEXT_PUBLIC_BACKEND_URL`)
