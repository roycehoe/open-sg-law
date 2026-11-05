"""add legislation

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-05 15:00:00.000000

"""

from typing import Optional, Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: Optional[Union[str, Sequence[str]]] = "0004"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.create_table(
        "legislation",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sso_code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("is_in_newest_listing", sa.Boolean(), nullable=False),
        sa.Column("listing_source", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["listing_source"], ["source.name"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sso_code"),
    )


def downgrade() -> None:
    op.drop_table("legislation")
