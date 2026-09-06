"""associate jobs with a reachout agent

Revision ID: 0003_add_reachout_agent
Revises: 0002_add_job_agent
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_add_reachout_agent"
down_revision = "0002_add_job_agent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("reachout_agent_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_jobs_reachout_agent_id_agents", "jobs", "agents", ["reachout_agent_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_jobs_reachout_agent_id_agents", "jobs", type_="foreignkey")
    op.drop_column("jobs", "reachout_agent_id")
