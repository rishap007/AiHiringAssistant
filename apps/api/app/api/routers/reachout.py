from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.agent import Agent
from app.models.call import Call
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.search_run import SearchRun
from app.schemas.hiring import (
    AgentRead,
    CandidateRead,
    CandidatePhoneUpdate,
    CallRead,
    JobDescriptionUpdate,
    JobRead,
    ReachoutDashboardRead,
)
from app.services.hunar_client import HunarAPIError, HunarClient
from app.services.jd_parser import JDParseError, parse_job_description
from app.services.people_search import get_people_search_client

router = APIRouter(tags=["reachout"])


async def _sync_call_from_hunar(call: Call, hunar_client: HunarClient, db: Session) -> None:
    """Refresh a reachout call so the dashboard works even if a webhook is delayed."""
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


async def get_hunar_client() -> AsyncIterator[HunarClient]:
    client = HunarClient()
    try:
        yield client
    finally:
        await client.aclose()


def get_job(db: Session, job_id: UUID) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/jobs/{job_id}", response_model=JobRead)
def update_job(job_id: UUID, payload: JobDescriptionUpdate, db: Session = Depends(get_db)) -> Job:
    job = get_job(db, job_id)
    job.jd_raw_text = payload.jd_raw_text
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{job_id}/parse")
async def parse_job(job_id: UUID, db: Session = Depends(get_db)) -> dict[str, Any]:
    job = get_job(db, job_id)
    if not job.jd_raw_text:
        raise HTTPException(status_code=400, detail="Job has no jd_raw_text to parse")
    try:
        parsed = await parse_job_description(job.jd_raw_text)
    except JDParseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    job.jd_parsed_json = parsed
    db.commit()
    return parsed


@router.post("/jobs/{job_id}/search", response_model=list[CandidateRead], status_code=status.HTTP_201_CREATED)
async def search_candidates(job_id: UUID, db: Session = Depends(get_db)) -> list[Candidate]:
    job = get_job(db, job_id)
    if not job.jd_parsed_json:
        raise HTTPException(status_code=400, detail="Parse the job description before searching")
    client = get_people_search_client()
    results = await client.search(job.jd_parsed_json)
    candidates = [
        Candidate(
            job_id=job.id,
            name=result.name,
            phone_e164=result.phone_e164,
            email=result.email,
            headline=result.headline,
            source=result.source,
            source_ref=result.source_ref,
        )
        for result in results
    ]
    db.add_all(candidates)
    db.add(
        SearchRun(
            job_id=job.id,
            provider=results[0].source if results else settings.people_search_provider,
            query_json=job.jd_parsed_json,
            result_count=len(results),
        )
    )
    db.commit()
    for candidate in candidates:
        db.refresh(candidate)
    return candidates


@router.patch("/jobs/{job_id}/candidates/{candidate_id}", response_model=CandidateRead)
def update_candidate_phone(
    job_id: UUID, candidate_id: UUID, payload: CandidatePhoneUpdate, db: Session = Depends(get_db)
) -> Candidate:
    get_job(db, job_id)
    candidate = db.scalar(select(Candidate).where(Candidate.id == candidate_id, Candidate.job_id == job_id))
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found for this job")
    candidate.phone_e164 = payload.phone_e164
    db.commit()
    db.refresh(candidate)
    return candidate


async def create_reachout_agent(job: Job, db: Session, hunar_client: HunarClient) -> Agent:
    if job.reachout_agent is not None:
        return job.reachout_agent
    try:
        response = await hunar_client.create_agent(
            name=f"Reachout — {job.title}",
            language="ENGLISH",
            voice_persona="NEHA",
            objective=f"Gauge outbound interest from passive candidates for the {job.title} role and collect their availability, in a low-pressure, respectful tone.",
            agent_prompt=(
                f"You are {{persona_name}} calling on behalf of a company hiring for {job.title}. This person did not apply — "
                "you are reaching out proactively. Be upfront about that, keep it brief, gauge whether they'd be open to "
                "hearing more, and if so ask about notice period. If not interested, thank them and end the call quickly."
            ),
            introduction="Hi {callee_name}, this is {persona_name} — I know this is out of the blue, I'm reaching out about a {job_role} opportunity. Is now an okay time for a 2-minute chat?",
            result_prompt="Determine whether the candidate is open to hearing more, their stated notice period in days if mentioned, and a one-sentence summary.",
            result_schema={"interested": "boolean", "notice_period_days": "number", "summary": "string"},
        )
    except HunarAPIError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    hunar_agent_id = response.get("id")
    if not hunar_agent_id:
        raise HTTPException(status_code=502, detail="Hunar response did not include an agent id")
    agent = Agent(hunar_agent_id=str(hunar_agent_id), purpose="reachout", name=f"Reachout — {job.title}", language="ENGLISH", voice_persona="NEHA")
    db.add(agent)
    db.flush()
    job.reachout_agent_id = agent.id
    db.commit()
    db.refresh(agent)
    return agent


@router.post("/jobs/{job_id}/agent/reachout", response_model=AgentRead)
async def get_or_create_reachout_agent(
    job_id: UUID, db: Session = Depends(get_db), hunar_client: HunarClient = Depends(get_hunar_client)
) -> Agent:
    return await create_reachout_agent(get_job(db, job_id), db, hunar_client)


@router.post("/jobs/{job_id}/candidates/{candidate_id}/reachout-call", response_model=CallRead, status_code=status.HTTP_201_CREATED)
async def trigger_reachout_call(
    job_id: UUID, candidate_id: UUID, db: Session = Depends(get_db), hunar_client: HunarClient = Depends(get_hunar_client)
) -> Call:
    job = get_job(db, job_id)
    candidate = db.scalar(select(Candidate).where(Candidate.id == candidate_id, Candidate.job_id == job_id))
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found for this job")
    if job.reachout_agent is None:
        raise HTTPException(status_code=400, detail="Create the reachout agent before triggering a call")
    if not candidate.phone_e164:
        raise HTTPException(status_code=400, detail="Candidate phone_e164 is required before calling")
    try:
        response = await hunar_client.create_call(
            agent_id=job.reachout_agent.hunar_agent_id,
            callee_name=candidate.name,
            mobile_number=candidate.phone_e164,
            custom_data={"job_role": job.title},
            retry_config={"max_retry_count": 1, "retry_interval_hours": 6},
        )
    except HunarAPIError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    call = Call(
        hunar_call_id=str(response["id"]), agent_id=job.reachout_agent.id, candidate_id=candidate.id, job_id=job.id,
        status="NOT_STARTED", lifecycle_status="NOT_STARTED", request_id=response.get("request_id"),
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )
    db.add(call)
    db.commit()
    db.refresh(call)
    return call


@router.get("/jobs/{job_id}/reachout-dashboard", response_model=list[ReachoutDashboardRead])
async def reachout_dashboard(
    job_id: UUID,
    db: Session = Depends(get_db),
    hunar_client: HunarClient = Depends(get_hunar_client),
) -> list[dict[str, Any]]:
    _ = get_job(db, job_id)
    stored_calls = list(db.scalars(select(Call).where(Call.job_id == job_id)).all())
    for call in stored_calls:
        await _sync_call_from_hunar(call, hunar_client, db)
    rows = db.execute(
        select(Candidate, Call.status, Call.result_json)
        .outerjoin(Call, (Call.candidate_id == Candidate.id) & (Call.job_id == job_id))
        .where(Candidate.job_id == job_id)
        .order_by(Candidate.created_at.desc())
    ).all()
    return [
        {"id": candidate.id, "name": candidate.name, "phone_e164": candidate.phone_e164, "email": candidate.email,
         "headline": candidate.headline, "source": candidate.source, "source_ref": candidate.source_ref,
         "call_status": call_status, "result_json": result_json}
        for candidate, call_status, result_json in rows
    ]
