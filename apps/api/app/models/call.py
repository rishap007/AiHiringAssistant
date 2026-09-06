from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class Call(Base):
    __tablename__ = "calls"
    __table_args__ = (UniqueConstraint("hunar_call_id"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hunar_call_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    candidate_id: Mapped[UUID] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    job_id: Mapped[UUID | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String, nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(String, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_status: Mapped[str | None] = mapped_column(String, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    agent: Mapped["Agent"] = relationship(back_populates="calls")
    candidate: Mapped["Candidate"] = relationship(back_populates="calls")
    job: Mapped["Job | None"] = relationship(back_populates="calls")
