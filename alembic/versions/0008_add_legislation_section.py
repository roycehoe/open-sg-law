"""add legislation section

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-05 18:00:00.000000

"""

from typing import Optional, Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: Optional[Union[str, Sequence[str]]] = "0007"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.create_table(
        "legislation_section",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("printed_number", sa.Text(), nullable=False),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("part_heading", sa.Text(), nullable=True),
        sa.Column("division_heading", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("first_page_number", sa.Integer(), nullable=False),
        sa.Column("last_page_number", sa.Integer(), nullable=False),
        sa.Column("sso_anchor", sa.Text(), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("is_repealed", sa.Boolean(), nullable=False),
        sa.Column("is_on_image_page", sa.Boolean(), nullable=False),
        sa.Column("legislation_version_id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('SECTION', 'ARTICLE', 'SCHEDULE')",
            name="ck_legislation_section_kind",
        ),
        sa.ForeignKeyConstraint(["legislation_version_id"], ["legislation_version.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "legislation_version_id",
            "ordinal",
            name="uq_legislation_section_legislation_version_id_ordinal",
        ),
    )
    op.create_index(
        "ix_legislation_section_legislation_version_id",
        "legislation_section",
        ["legislation_version_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_legislation_section_legislation_version_id",
        table_name="legislation_section",
    )
    op.drop_table("legislation_section")
