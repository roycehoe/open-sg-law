"""add legislation version

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-05 17:00:00.000000

"""

from typing import Optional, Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: Optional[Union[str, Sequence[str]]] = "0006"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.create_table(
        "legislation_version",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("printed_version_date", sa.Text(), nullable=True),
        sa.Column("version_date", sa.Date(), nullable=True),
        sa.Column("version_stamp", sa.Text(), nullable=True),
        sa.Column("archive_timestamp", sa.Text(), nullable=True),
        sa.Column("archive_digest", sa.Text(), nullable=True),
        sa.Column("body_character_count", sa.Integer(), nullable=True),
        sa.Column("section_character_count", sa.Integer(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_newest", sa.Boolean(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("legislation_id", sa.Integer(), nullable=False),
        sa.Column("source_response_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["legislation_id"], ["legislation.id"]),
        sa.ForeignKeyConstraint(["source"], ["source.name"]),
        sa.ForeignKeyConstraint(["source_response_id"], ["source_response.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_response_id"),
    )
    op.create_index(
        "ix_legislation_version_legislation_id",
        "legislation_version",
        ["legislation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_legislation_version_legislation_id", table_name="legislation_version"
    )
    op.drop_table("legislation_version")
