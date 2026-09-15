"""Real Web Push notifications -- reaches a user even with no tab open, using
the standard W3C Push API. No third-party service and no paid API: pushes go
directly to the browser vendor's own free push endpoint (Chrome -> Google,
Firefox -> Mozilla), authenticated with VAPID keys generated and held
locally, not issued by anyone. Requires HTTPS or localhost on the frontend
(a browser security requirement for service workers, not something this
code can work around) -- fine for local dev, a real constraint for any
future deployment elsewhere.
"""
import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from py_vapid import Vapid
from pywebpush import WebPushException
from pywebpush import webpush as _webpush

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
VAPID_PRIVATE_KEY_PATH = DATA_DIR / "vapid_private_key.pem"
# VAPID requires a contact URI in the claims; this is a placeholder, not a
# real monitored address -- fine for a demo, worth replacing for anything
# beyond one.
VAPID_CLAIMS_EMAIL = "mailto:orca-demo@example.com"


def _ensure_vapid_key() -> Vapid:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Vapid.from_file is a classmethod: it loads the key if the file exists,
    # or generates and persists a new one if it doesn't -- it does NOT
    # mutate an existing instance in place.
    return Vapid.from_file(str(VAPID_PRIVATE_KEY_PATH))


def get_vapid_public_key_b64() -> str:
    vapid = _ensure_vapid_key()
    pub_bytes = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(pub_bytes).decode().rstrip("=")


def send_push(subscription_info: dict, payload: dict) -> bool:
    _ensure_vapid_key()
    try:
        _webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=str(VAPID_PRIVATE_KEY_PATH),
            vapid_claims={"sub": VAPID_CLAIMS_EMAIL},
        )
        return True
    except WebPushException:
        return False
