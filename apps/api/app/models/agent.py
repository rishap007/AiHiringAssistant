from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    hunar_agent_id: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=False, default="ENGLISH")
    voice_persona: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    calls: Mapped[list["Call"]] = relationship(back_populates="agent")
    jobs: Mapped[list["Job"]] = relationship(back_populates="agent", foreign_keys="Job.agent_id")
    reachout_jobs: Mapped[list["Job"]] = relationship(
        back_populates="reachout_agent", foreign_keys="Job.reachout_agent_id"
    )
