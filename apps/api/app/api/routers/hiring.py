from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.agent import Agent
from app.models.call import Call
from app.models.candidate import Candidate
from app.models.job import Job
from app.schemas.hiring import (
    AgentRead,
    CallRead,
    CandidateCreate,
    CandidateRead,
    JobCallRead,
    JobCreate,
    JobRead,
)
from app.services.hunar_client import HunarAPIError, HunarClient

router = APIRouter(tags=["hiring"])


async def get_hunar_client() -> AsyncIterator[HunarClient]:
    client = HunarClient()
    try:
        yield client
    finally:
        await client.aclose()


def _get_job(db: Session, job_id: UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def _sync_call_from_hunar(call: Call, hunar_client: HunarClient, db: Session) -> None:
    """Refresh a stored call from Hunar so local development does not require webhooks."""
    try:
        remote = await hunar_client.get_call(call.hunar_call_id)
    except HunarAPIError:
        return

    for field in ("status", "lifecycle_status", "recording_url", "engagement_status"):
        if field in remote:
            setattr(call, field, remote[field])
    if "result_json" in remote:
        call.result_json = remote["result_json"]
    elif "result" in remote:
        call.result_json = remote["result"]
    if "duration_seconds" in remote:
        call.duration_seconds = remote["duration_seconds"]
    elif "duration_minutes" in remote:
        call.duration_seconds = float(remote["duration_minutes"]) * 60
    db.commit()


@router.post("/jobs", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> Job:
    job = Job(title=payload.title, description=payload.description)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)) -> list[Job]:
    return list(db.scalars(select(Job).order_by(Job.created_at.desc())).all())


@router.post("/jobs/{job_id}/candidates", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def add_candidate(job_id: UUID, payload: CandidateCreate, db: Session = Depends(get_db)) -> Candidate:
    _get_job(db, job_id)
    candidate = Candidate(job_id=job_id, name=payload.name, phone_e164=payload.phone_e164, source="manual")
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get("/jobs/{job_id}/candidates", response_model=list[CandidateRead])
def list_job_candidates(job_id: UUID, db: Session = Depends(get_db)) -> list[Candidate]:
    _get_job(db, job_id)
    return list(
        db.scalars(
            select(Candidate)
            .where(Candidate.job_id == job_id)
            .order_by(Candidate.created_at.desc())
        ).all()
    )


@router.post("/jobs/{job_id}/agent", response_model=AgentRead)
async def create_or_reuse_agent(
    job_id: UUID,
    db: Session = Depends(get_db),
    hunar_client: HunarClient = Depends(get_hunar_client),
) -> Agent:
    job = _get_job(db, job_id)
    if job.agent is not None:
        return job.agent

    try:
        response = await hunar_client.create_agent(
            name=f"Screening — {job.title}",
            language="ENGLISH",
            voice_persona="NEHA",
            objective=(
                f"Screen candidates for the {job.title} role by assessing interest, relevant experience, "
                "and availability, in a friendly and professional tone."
            ),
            agent_prompt=(
                f"You are {{persona_name}}, a recruiting assistant calling on behalf of the hiring team for the "
                f"{job.title} position. Job summary: {job.description}. Ask about the candidate's current role, "
                "relevant experience, interest in this role, and notice period. Be concise, warm, and respectful "
                "of their time. If they are not interested, thank them and end the call politely."
            ),
            introduction="Hi {callee_name}, this is {persona_name} calling about the {job_role} opening you applied for. Do you have a couple of minutes?",
            result_prompt=(
                "From this conversation, determine whether the candidate is qualified based on stated experience, "
                "whether they are interested in proceeding, their notice period in days if mentioned, and a "
                "one-sentence summary of the call."
            ),
            result_schema={
                "qualified": "boolean",
                "interested": "boolean",
                "notice_period_days": "number",
                "summary": "string",
            },
        )
    except HunarAPIError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc

    hunar_agent_id = response.get("id")
    if not hunar_agent_id:
        raise HTTPException(status_code=502, detail="Hunar response did not include an agent id")
    agent = Agent(
        hunar_agent_id=str(hunar_agent_id),
        purpose="screening",
        name=f"Screening — {job.title}",
        language="ENGLISH",
        voice_persona="NEHA",
    )
    db.add(agent)
    db.flush()
    job.agent_id = agent.id
    db.commit()
    db.refresh(agent)
    return agent


@router.post("/jobs/{job_id}/candidates/{candidate_id}/call", response_model=CallRead, status_code=status.HTTP_201_CREATED)
async def trigger_candidate_call(
    job_id: UUID,
    candidate_id: UUID,
    db: Session = Depends(get_db),
    hunar_client: HunarClient = Depends(get_hunar_client),
) -> Call:
    job = _get_job(db, job_id)
    candidate = db.scalar(select(Candidate).where(Candidate.id == candidate_id, Candidate.job_id == job_id))
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found for this job")
    if job.agent is None:
        raise HTTPException(status_code=400, detail="Create the screening agent before triggering a call")
    if not candidate.phone_e164:
        raise HTTPException(status_code=400, detail="Candidate phone_e164 is required before calling")

    try:
        response = await hunar_client.create_call(
            agent_id=job.agent.hunar_agent_id,
            callee_name=candidate.name,
            mobile_number=candidate.phone_e164,
            custom_data={"job_role": job.title},
            retry_config={"max_retry_count": 1, "retry_interval_hours": 6},
        )
    except HunarAPIError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc

    hunar_call_id = response.get("id")
    if not hunar_call_id:
        raise HTTPException(status_code=502, detail="Hunar response did not include a call id")
    call = Call(
        hunar_call_id=str(hunar_call_id),
        agent_id=job.agent.id,
        candidate_id=candidate.id,
        job_id=job.id,
        status="NOT_STARTED",
        lifecycle_status="NOT_STARTED",
        request_id=response.get("request_id"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


@router.get("/jobs/{job_id}/calls", response_model=list[JobCallRead])
async def list_job_calls(
    job_id: UUID,
    db: Session = Depends(get_db),
    hunar_client: HunarClient = Depends(get_hunar_client),
) -> list[dict[str, Any]]:
    _get_job(db, job_id)
    stored_calls = list(db.scalars(select(Call).where(Call.job_id == job_id).order_by(Call.created_at.desc())).all())
    for call in stored_calls:
        await _sync_call_from_hunar(call, hunar_client, db)
    rows = db.execute(
        select(Call, Candidate.name)
        .join(Candidate, Candidate.id == Call.candidate_id)
        .where(Call.job_id == job_id)
        .order_by(Call.created_at.desc())
    ).all()
    return [
        {
            "id": call.id,
            "hunar_call_id": call.hunar_call_id,
            "candidate_name": candidate_name,
            "status": call.status,
            "result_json": call.result_json,
            "recording_url": call.recording_url,
            "duration_seconds": call.duration_seconds,
        }
        for call, candidate_name in rows
    ]
