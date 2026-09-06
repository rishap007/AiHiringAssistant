from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HiringSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class JobCreate(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


class JobRead(HiringSchema):
    id: UUID
    title: str
    description: str
    agent_id: UUID | None = None
    reachout_agent_id: UUID | None = None
    created_at: datetime


class CandidateCreate(BaseModel):
    name: str = Field(min_length=1)
    phone_e164: str | None = None


class CandidatePhoneUpdate(BaseModel):
    phone_e164: str = Field(min_length=1)


class CandidateRead(HiringSchema):
    id: UUID
    job_id: UUID | None
    name: str
    phone_e164: str | None
    email: str | None
    source: str
    source_ref: str | None
    headline: str | None
    created_at: datetime


class AgentRead(HiringSchema):
    id: UUID
    hunar_agent_id: str
    purpose: str
    name: str
    language: str
    voice_persona: str
    created_at: datetime


class CallRead(HiringSchema):
    id: UUID
    hunar_call_id: str
    agent_id: UUID
    candidate_id: UUID
    job_id: UUID | None
    status: str
    lifecycle_status: str
    result_json: dict[str, Any] | None
    recording_url: str | None
    duration_seconds: float | None
    engagement_status: str | None
    request_id: str | None
    created_at: datetime
    updated_at: datetime


class JobCallRead(BaseModel):
    id: UUID
    hunar_call_id: str
    candidate_name: str
    status: str
    result_json: dict[str, Any] | None
    recording_url: str | None
    duration_seconds: float | None


class JobDescriptionUpdate(BaseModel):
    jd_raw_text: str = Field(min_length=1)


class CandidateDashboardRead(BaseModel):
    id: UUID
    name: str
    phone_e164: str | None
    email: str | None
    headline: str | None
    source: str
    source_ref: str | None


class ReachoutDashboardRead(CandidateDashboardRead):
    call_status: str | None = None
    result_json: dict[str, Any] | None = None
