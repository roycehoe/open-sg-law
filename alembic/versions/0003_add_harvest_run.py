"""add harvest run

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-05 13:45:00.000000

"""

from typing import Optional, Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: Optional[Union[str, Sequence[str]]] = "0002"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.create_table(
        "harvest_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requests_sent", sa.Integer(), nullable=False),
        sa.Column("bodies_stored", sa.Integer(), nullable=False),
        sa.Column("bodies_unchanged", sa.Integer(), nullable=False),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("halt_reason", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'SUCCEEDED', 'HALTED', 'FAILED')",
            name="ck_harvest_run_status",
        ),
        sa.ForeignKeyConstraint(["source"], ["source.name"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_harvest_run_source_started_at", "harvest_run", ["source", "started_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_harvest_run_source_started_at", table_name="harvest_run")
    op.drop_table("harvest_run")
