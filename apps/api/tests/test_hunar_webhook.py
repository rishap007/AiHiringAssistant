import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.core.config import settings
from app.main import app
from app.models.agent import Agent
from app.models.call import Call
from app.models.candidate import Candidate

TEST_KEY = "test-hunar-key"
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def client():
    original_api_key = settings.hunar_api_key
    settings.hunar_api_key = TEST_KEY
    Base.metadata.create_all(engine)
    db = TestingSessionLocal()
    agent = Agent(hunar_agent_id="hunar-agent-1", purpose="screening", name="Screening", voice_persona="professional")
    candidate = Candidate(name="Asha Rao", source="mock")
    db.add_all([agent, candidate])
    db.flush()
    call = Call(
        hunar_call_id="hunar-call-1",
        agent_id=agent.id,
        candidate_id=candidate.id,
        status="initiated",
        lifecycle_status="created",
    )
    db.add(call)
    db.commit()
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    settings.hunar_api_key = original_api_key
    Base.metadata.drop_all(engine)


def signed_headers(body: bytes, timestamp: str) -> dict[str, str]:
    message = f"{timestamp}.".encode() + body
    signature = base64.b64encode(hmac.new(TEST_KEY.encode(), message, hashlib.sha256).digest()).decode()
    return {"X-Hunar-Signature": signature, "X-Hunar-Timestamp": timestamp}


def test_signed_status_and_summary_events_update_call(client: TestClient) -> None:
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    status_payload = {
        "event_type": "call_status_updated",
        "call_id": "hunar-call-1",
        "status": "completed",
        "lifecycle_status": "ended",
        "engagement_status": "answered",
    }
    status_body = json.dumps(status_payload, separators=(",", ":")).encode()
    response = client.post("/webhooks/hunar", content=status_body, headers=signed_headers(status_body, timestamp))
    assert response.status_code == 200

    summary_payload = {
        "event_type": "call_summary",
        "call_id": "hunar-call-1",
        "result_json": {"screened": True},
        "recording_url": "https://cdn.hunar.ai/recordings/hunar-call-1.mp3",
        "duration_seconds": 92.5,
    }
    summary_body = json.dumps(summary_payload, separators=(",", ":")).encode()
    response = client.post("/webhooks/hunar", content=summary_body, headers=signed_headers(summary_body, timestamp))
    assert response.status_code == 200

    db = TestingSessionLocal()
    call = db.query(Call).filter_by(hunar_call_id="hunar-call-1").one()
    assert call.status == "completed"
    assert call.lifecycle_status == "ended"
    assert call.result_json == {"screened": True}
    assert call.recording_url.endswith(".mp3")
    assert call.duration_seconds == 92.5
    db.close()


def test_missing_or_invalid_signature_returns_401(client: TestClient) -> None:
    body = b'{"event_type":"call_summary","call_id":"hunar-call-1"}'
    response = client.post("/webhooks/hunar", content=body)
    assert response.status_code == 401

    response = client.post(
        "/webhooks/hunar",
        content=body,
        headers={"X-Hunar-Signature": "invalid", "X-Hunar-Timestamp": str(int(datetime.now().timestamp()))},
    )
    assert response.status_code == 401
