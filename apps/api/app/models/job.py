from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    agent_id: Mapped[UUID | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    reachout_agent_id: Mapped[UUID | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    jd_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    jd_parsed_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    candidates: Mapped[list["Candidate"]] = relationship(back_populates="job")
    calls: Mapped[list["Call"]] = relationship(back_populates="job")
    search_runs: Mapped[list["SearchRun"]] = relationship(back_populates="job")
    agent: Mapped["Agent | None"] = relationship(back_populates="jobs", foreign_keys=[agent_id])
    reachout_agent: Mapped["Agent | None"] = relationship(
        back_populates="reachout_jobs", foreign_keys=[reachout_agent_id]
    )
