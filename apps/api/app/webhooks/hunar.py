from __future__ import annotations

import base64
import hashlib
import hmac
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.call import Call

router = APIRouter()
SUPPORTED_EVENTS = {
    "call_status_updated",
    "call_recording_done",
    "call_result_done",
    "call_summary",
}


def compute_hunar_signature(api_key: str, request_body: bytes, timestamp: str) -> str:
    message = f"{timestamp}.".encode() + request_body
    digest = hmac.new(api_key.encode(), message, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def verify_hunar_webhook_signature(
    signature_header: str | None,
    timestamp_header: str | None,
    request_body: bytes,
    trusted_api_keys: list[str],
) -> bool:
    if not signature_header or not timestamp_header or not trusted_api_keys:
        return False
    try:
        timestamp = float(timestamp_header)
    except (TypeError, ValueError):
        return False
    if abs(time.time() - timestamp) > 300:
        return False

    received_signatures = [segment.strip() for segment in signature_header.split(",") if segment.strip()]
    return any(
        hmac.compare_digest(compute_hunar_signature(api_key, request_body, timestamp_header), received)
        for api_key in trusted_api_keys
        for received in received_signatures
    )


def _apply_call_event(call: Call, payload: dict[str, Any]) -> None:
    direct_fields = (
        "status",
        "lifecycle_status",
        "recording_url",
        "result_json",
        "duration_seconds",
        "engagement_status",
    )
    for field in direct_fields:
        if field in payload:
            setattr(call, field, payload[field])

    # Hunar summary examples use these names for the same stored values.
    if "result_json" not in payload and "result" in payload:
        call.result_json = payload["result"]
    if "duration_seconds" not in payload:
        if "duration_minutes" in payload:
            call.duration_seconds = float(payload["duration_minutes"]) * 60
        elif "duration" in payload:
            call.duration_seconds = payload["duration"]

    call.updated_at = datetime.now(timezone.utc)


@router.post("/webhooks/hunar", status_code=200)
async def receive_hunar_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    request_body = await request.body()
    signature_header = request.headers.get("x-hunar-signature")
    timestamp_header = request.headers.get("x-hunar-timestamp")
    if not verify_hunar_webhook_signature(
        signature_header,
        timestamp_header,
        request_body,
        [settings.hunar_api_key],
    ):
        raise HTTPException(status_code=401, detail="Invalid Hunar webhook signature")

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be a JSON object")

    if payload.get("event_type") not in SUPPORTED_EVENTS:
        return {"status": "ok"}

    hunar_call_id = payload.get("call_id")
    if not hunar_call_id:
        raise HTTPException(status_code=400, detail="Webhook payload is missing call_id")

    call = db.scalar(select(Call).where(Call.hunar_call_id == hunar_call_id))
    if call is not None:
        _apply_call_event(call, payload)
        db.commit()
    return {"status": "ok"}
