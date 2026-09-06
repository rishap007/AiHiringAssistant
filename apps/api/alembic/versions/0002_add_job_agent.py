"""associate jobs with their screening agent

Revision ID: 0002_add_job_agent
Revises: 0001_initial_models
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_add_job_agent"
down_revision = "0001_initial_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_jobs_agent_id_agents", "jobs", "agents", ["agent_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_jobs_agent_id_agents", "jobs", type_="foreignkey")
    op.drop_column("jobs", "agent_id")
