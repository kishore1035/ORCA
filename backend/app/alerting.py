"""Proactive hazard alerting, delivered two ways:

1. In-app, over a long-lived SSE connection, while the browser tab is open
   (subscribe/unsubscribe/publish below).
2. Real Web Push (app/push.py), reaching a session even with no tab open --
   as long as it has subscribed via the browser's PushManager at least once
   and the OS/browser push service is willing to deliver (best-effort, no
   delivery guarantee is possible with any push system).

Every `interval_seconds`, every session with a known last-resolved location
(set after a normal /chat turn) gets re-checked against live weather + risk
conditions -- the same weather_agent/risk_agent used by the main pipeline,
not new hazard logic. An alert is only published on a TRANSITION into
"unsafe" (not repeated on every poll while still unsafe, and not on
recovering to "safe"), to avoid spamming a subscriber.
"""
import asyncio
import logging

from app import db, push
from app.agents.risk_agent import run_risk_agent
from app.agents.weather_agent import run_weather_agent

logger = logging.getLogger(__name__)

DEFAULT_CHECK_INTERVAL_SECONDS = 300

_subscribers: dict[str, list[asyncio.Queue]] = {}


def subscribe(session_id: str) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(session_id, []).append(queue)
    return queue


def unsubscribe(session_id: str, queue: asyncio.Queue) -> None:
    queues = _subscribers.get(session_id)
    if not queues:
        return
    if queue in queues:
        queues.remove(queue)
    if not queues:
        _subscribers.pop(session_id, None)


def publish(session_id: str, alert: dict) -> None:
    for queue in _subscribers.get(session_id, []):
        queue.put_nowait(alert)


async def _send_web_push(session_id: str, alert: dict) -> None:
    subscriptions = db.get_push_subscriptions(session_id)
    if not subscriptions:
        return
    payload = {
        "title": f"ORCA hazard alert: {alert['verdict']}",
        "body": "; ".join(alert["reasons"]),
    }
    for subscription in subscriptions:
        try:
            await asyncio.to_thread(push.send_push, subscription, payload)
        except Exception:
            logger.warning("web push delivery failed for session %s", session_id, exc_info=True)


async def check_hazards_once() -> None:
    for tracked in db.get_tracked_sessions():
        session_id, lat, lon = tracked["session_id"], tracked["lat"], tracked["lon"]
        try:
            weather, _ = await run_weather_agent(lat, lon)
            risk, _ = await run_risk_agent(lat, lon, weather)
        except Exception:
            logger.warning("proactive hazard check failed for session %s", session_id, exc_info=True)
            continue

        verdict = risk["verdict"]
        previous_verdict = db.get_last_verdict(session_id)
        if verdict == "unsafe" and previous_verdict != "unsafe":
            alert = {"type": "alert", "verdict": verdict, "reasons": risk["reasons"], "lat": lat, "lon": lon}
            publish(session_id, alert)
            await _send_web_push(session_id, alert)
        db.set_last_verdict(session_id, verdict)


async def run_periodic_checks(interval_seconds: int = DEFAULT_CHECK_INTERVAL_SECONDS) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        await check_hazards_once()
