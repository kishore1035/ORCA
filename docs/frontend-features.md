# ORCA Frontend — Required Features

This document lists every feature the ORCA frontend (`frontend/`) needs to support, derived from the backend's actual API contract (`backend/app/main.py`, `backend/app/schemas.py`, `backend/app/graph.py`). It's a checklist for what "done" looks like for the frontend, not a UI style guide — see `docs/data-sources.md` for the data sources behind each feature and the root `CLAUDE.md` for architecture rationale.

Each feature names the backend contract it depends on and the component that currently implements it (all present as of this writing — see "Status" column).

---

## 1. Authentication gate

**Backend**: `POST /auth/signup`, `POST /auth/login` → `{token, user_id, email}` (`AuthResponse`). Every other endpoint requires `Authorization: Bearer <token>` (or `?token=` for the SSE alert stream, since `EventSource` can't set headers).

**Required behavior:**
- Signup and login forms, both hitting the same shape of response.
- Persist the token (and email) across reloads — `localStorage`, not memory-only.
- Gate the entire app behind a valid token: no chat UI, no history fetch, no alert subscription until authenticated.
- Log out: clear stored auth and return to the gate.
- Surface auth errors (wrong password, duplicate email on signup) without crashing the form.

**Status:** implemented — `components/AuthGate.tsx`, `app/page.tsx` (`loadStoredAuth`/`storeAuth`, `AUTH_STORAGE_KEY`).

---

## 2. Session identity and persisted history

**Backend**: `GET /sessions/{session_id}/history` returns prior turns; `POST /chat` doesn't trust client-sent history — the backend loads it from SQLite by `session_id` and persists both sides of every turn itself.

**Required behavior:**
- Generate (or reuse) a stable per-browser `session_id`, scoped by the logged-in user's email so switching accounts doesn't leak another user's session id.
- On mount, fetch and render prior history for that session — restoring a conversation across reloads, not just within one page life.
- A session that already belongs to another user must fail gracefully (backend returns 403 `SessionOwnershipError`) rather than silently overwriting someone else's session.

**Status:** implemented — `getOrCreateSessionId()` + `fetchHistory()` in `app/page.tsx` / `lib/chatClient.ts`.

---

## 3. Streaming chat (the core feature)

**Backend**: `POST /chat` streams Server-Sent Events over a POST body — `event: trace` (one per agent node: `planner`, `geospatial`, `weather`, `risk`, `ocean_analytics`, `route`) followed by one `event: answer` with the final payload (`answer`, `risk`, `verification`, `what_if`, `evidence`, `location`). Native `EventSource` doesn't support POST, so this must be hand-parsed via `fetch` + `ReadableStream`, not `EventSource`.

**Required behavior:**
- Text input + submit, disabled while a response is streaming.
- Append the user's message immediately (optimistic), then stream in trace entries as they arrive, then the final assistant message.
- Update derived UI state as trace entries arrive, not just at the end: capture `lat`/`lon` from the `geospatial` trace entry (for the map), capture `waypoints` from the `route` trace entry.
- Handle a network/stream failure mid-request without leaving the UI stuck in "streaming" state forever.
- Quick-prompt buttons for demo/golden-path queries (safety check, what-if, nearest fishing zone, cyclone/lightning alerts) — disabled while streaming.

**Status:** implemented — `lib/chatClient.ts` (`streamChat`), `components/ChatPanel.tsx`, `handleSend()` in `app/page.tsx`.

---

## 4. Reasoning trace visualization

**Backend**: every graph node appends a `TraceEntry{agent, inputs, output, sources, fetched_at, is_cached}` — this trace *is* the "make agentic reasoning visible" requirement, not optional debug logging.

**Required behavior:**
- Render each trace entry as it streams in (agent name, what it looked up, what it returned), so a user can watch the pipeline reason step by step, not just wait for a final answer.
- Show data provenance per entry: `sources`, `fetched_at`, and whether it's `is_cached` (stale/fallback data) vs. live.
- Render the 7-day SST trend (`sst_trend_celsius` inside the `ocean_analytics` entry's output) as a chart, not raw JSON — the connector fetches real history specifically so this can be visualized.

**Status:** implemented — `components/ReasoningTrace.tsx`, `components/SstTrendChart.tsx` (inline SVG sparkline).

---

## 5. Map view

**Backend**: `geospatial` trace entry carries `lat`/`lon`, `nearest_boundary`, `within_warning_zone`, `geofence_warning`; a route query's `route` trace entry carries `waypoints: [{lat, lon, verdict, reasons}]`.

**Required behavior:**
- Plot the resolved query location as a marker.
- For a route query, render every waypoint as a marker with a popup showing that waypoint's `verdict`/`reasons`, and draw the path as colored segments — red across any hazardous waypoint pair, green otherwise (don't just draw one uniform line; the color-per-segment *is* the safety signal).
- Must load client-side only (Leaflet touches `window`) — `next/dynamic` with `ssr: false`, not a plain import.
- Label the current risk verdict/score on or near the map when available, not just in the chat panel.

**Status:** implemented — `components/MapView.tsx`, dynamically imported in `app/page.tsx`.

---

## 6. Recommendation hero (headline verdict)

**Backend**: `answer` event's `risk: RiskAssessment{risk_score, risk_level, factors, recommendation, confidence}` and `verification: VerificationResult{is_verified, sources, data_status, checks_passed, issues, confidence}`.

**Required behavior:**
- A prominent, above-the-fold verdict card per assistant message (not buried in prose) showing risk level, score, and top contributing factors.
- Surface verification status distinctly — a low-confidence or `INSUFFICIENT` data_status answer must not look identical to a fully-verified one.
- A loading/skeleton state while the corresponding request is still streaming (the hero can't render until the `answer` event lands, but the message list should not look broken while waiting).

**Status:** implemented — `components/RecommendationHero.tsx`, used in `ChatPanel.tsx` (including its `isLoading` state).

---

## 7. Evidence / grounding panel

**Backend**: `answer` event's `evidence: MarineParameter[]` — each a `{parameter, value, unit, latitude, longitude, timestamp, source, data_status, confidence, grid_distance_km}` — the literal numeric observations the answer is grounded in.

**Required behavior:**
- Collapsible/expandable list of every underlying observation cited, not just the synthesized text — a user (or judge) must be able to verify the answer against raw numbers.
- Show each parameter's `source` and `data_status` (`LIVE`/`FORECAST`/`CACHED`/`HISTORICAL`) so staleness is visible per-datapoint, not just per-answer.
- Pair with the `verification` result so "why is this trustworthy" is answerable from the UI alone.

**Status:** implemented — `components/EvidencePanel.tsx`, toggled per-message in `ChatPanel.tsx`.

---

## 8. What-if comparison

**Backend**: `answer` event's `what_if: WhatIfComparison{original_time, original_risk_score, original_risk_level, alternative_time, alternative_risk_score, alternative_risk_level, differences: WhatIfDifference[], verdict}` — populated only when the query is a what-if (different departure time, or a spatial move by N km in a direction).

**Required behavior:**
- Side-by-side comparison of the original vs. alternative scenario's risk level/score, only rendered when `what_if` is present on a message.
- Per-parameter delta breakdown (`differences`: parameter, original, alternative, delta, impact), not just the two headline scores.

**Status:** implemented — `components/WhatIfCard.tsx`, conditionally rendered in `ChatPanel.tsx`.

---

## 9. Proactive hazard alerts (in-app, SSE)

**Backend**: `GET /sessions/{session_id}/alerts/stream?token=...` — a long-lived SSE stream (native `EventSource` works here since it's GET-only) pushing `event: alert` with `{verdict, reasons, lat, lon}` only on a transition into/out of "unsafe" for that session's last-resolved location. 15s `: ping` keep-alive comments must be tolerated (ignored, not treated as malformed events).

**Required behavior:**
- Subscribe once authenticated, for the lifetime of the session (reconnect/cleanup on unmount).
- Show a dismissible banner on an incoming alert — must not require the user to be mid-conversation to see it.
- This channel only works while a tab is open; don't treat its absence as "no hazard" (see feature 10 for the no-tab case).

**Status:** implemented — `subscribeToAlerts()` in `lib/chatClient.ts`, alert banner in `app/page.tsx`.

---

## 10. Web push notifications (no tab required)

**Backend**: `GET /push/vapid-public-key` (public), `POST /push/subscribe` (auth-required) — real W3C Push API via VAPID, delivered through the browser vendor's push service, no third-party relay.

**Required behavior:**
- Feature-detect support (`PushManager`, `serviceWorker`) and hide the opt-in entirely when unsupported — don't show a dead button.
- An explicit opt-in action (not auto-subscribe): register the service worker, request `Notification.requestPermission()`, subscribe via `PushManager`, POST the subscription to the backend.
- A service worker that handles `push` and `notificationclick` — no offline app-shell caching needed, this is notification-only.
- Reflect subscribed/subscribing/error state in the UI so the user knows whether it's actually on.
- Requires HTTPS or `localhost` — expect it to silently not work on a plain-HTTP LAN deployment, and don't treat that as a bug to chase.

**Status:** implemented — `frontend/public/sw.js`, `lib/push.ts`, opt-in button in `app/page.tsx`.

---

## 11. Voice input/output

**Backend**: none — entirely client-side (Web Speech API), by explicit scope decision (no real SMS/phone/IVR at zero cost).

**Required behavior:**
- Feature-detected mic button that transcribes one utterance into the text input — hidden entirely in unsupported browsers, not just disabled.
- A "read answers aloud" toggle that speaks each new assistant message as it arrives, and stays off by default.
- Must not depend on `window` at module scope — the test environment has no DOM, so detection needs to degrade to "unsupported" rather than throwing at import time.

**Status:** implemented — `lib/voice.ts`, mic button + toggle in `ChatPanel.tsx`.

---

## 12. Geofence / boundary warnings

**Backend**: `geospatial` trace entry's `geofence_warning` (a deterministic, code-generated string — not left to LLM discretion) when `within_warning_zone` is true.

**Required behavior:**
- Surface this warning prominently whenever present, even if the user's question wasn't primarily about boundaries — the backend guarantees it's emitted precisely so the frontend/LLM answer can't bury it.

**Status:** implemented — synthesized into the answer text by the backend; the map (`nearest_boundary`) and reasoning trace both expose the underlying geospatial fields.

---

## 13. Responsive, dual-pane layout

**Required behavior:**
- Primary pane: chat (hero, what-if, message, evidence accordion) — should be the widest pane on desktop.
- Secondary pane: map (top half) + reasoning trace (bottom half) on desktop; must not simply disappear on narrower viewports — stack instead of clip.
- Top bar: authenticated user's email, push opt-in, logout — always visible, not nested in a menu that hides account state.

**Status:** implemented — `app/page.tsx`'s grid layout (`lg:grid-cols-12`, 7/5 split).

---

## Explicitly out of scope for the frontend

These are backend-only or deliberately unimplemented — don't add frontend affordances for them:
- Bathymetry-aware route planning (`route_agent.py` is a waypoint hazard *scan*, not a path planner — the frontend should not imply turn-by-turn navigation).
- Any non-browser voice channel (SMS/IVR).
- OAuth, email verification, or password reset (auth is intentionally email+password only).
- Editing or filtering historical trace/evidence data client-side — all filtering/thresholds are backend domain logic; the frontend renders what it's given.
