import json
import pytest
from starlette.testclient import TestClient
from app.main import app

def test_sse_chat_flow():
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"message": "Is it safe to fish off Mangaluru today?", "session_id": "pytest-test-1"},
    )
    assert response.status_code == 200
    lines = response.text.split("\n")
    events = [l for l in lines if l.startswith("event:")]
    assert len(events) > 0
    answer_payload = None
    for line in lines:
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                if "answer" in data:
                    answer_payload = data
                    break
            except Exception:
                pass
    assert answer_payload is not None
    assert "risk" in answer_payload
    assert answer_payload["risk"]["risk_level"] in ["HIGH", "CRITICAL", "MODERATE", "LOW", "EXTREME"]
    assert "factors" in answer_payload["risk"]
    assert len(answer_payload["risk"]["factors"]) > 0
    print("Answer risk level:", answer_payload["risk"]["risk_level"])
    print("Factors count:", len(answer_payload["risk"]["factors"]))
