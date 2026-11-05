"""add source response

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-05 14:00:00.000000

"""

from typing import Optional, Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: Optional[Union[str, Sequence[str]]] = "0003"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.create_table(
        "source_response",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requested_url", sa.Text(), nullable=False),
        sa.Column("final_url", sa.Text(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column("byte_length", sa.Integer(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("harvest_run_id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('LISTING_PAGE', 'DOCUMENT', 'CDX_ANSWER', 'ROBOTS_FILE')",
            name="ck_source_response_kind",
        ),
        sa.CheckConstraint(
            "(body_text IS NULL) <> (body_bytes IS NULL)",
            name="ck_source_response_one_body",
        ),
        sa.ForeignKeyConstraint(["harvest_run_id"], ["harvest_run.id"]),
        sa.ForeignKeyConstraint(["source"], ["source.name"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "requested_url", "sha256", name="uq_source_response_requested_url_sha256"
        ),
    )
    op.create_index(
        "ix_source_response_harvest_run_id", "source_response", ["harvest_run_id"]
    )
    op.create_index(
        "ix_source_response_source_kind", "source_response", ["source", "kind"]
    )


def downgrade() -> None:
    op.drop_index("ix_source_response_source_kind", table_name="source_response")
    op.drop_index("ix_source_response_harvest_run_id", table_name="source_response")
    op.drop_table("source_response")
