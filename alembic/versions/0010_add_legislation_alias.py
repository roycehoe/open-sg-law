"""add legislation alias

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-05 20:30:00.000000

"""

from typing import Optional, Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: Optional[Union[str, Sequence[str]]] = "0009"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.create_table(
        "legislation_alias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("legislation_id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('FULL_TITLE', 'TITLE_WITHOUT_YEAR', 'SSO_CODE')",
            name="ck_legislation_alias_kind",
        ),
        sa.ForeignKeyConstraint(["legislation_id"], ["legislation.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "legislation_id", "kind", name="uq_legislation_alias_legislation_id_kind"
        ),
    )
    op.create_index(
        "ix_legislation_alias_legislation_id",
        "legislation_alias",
        ["legislation_id"],
    )
    op.create_index(
        "ix_legislation_alias_lower_alias",
        "legislation_alias",
        [sa.text("lower(alias)")],
    )


def downgrade() -> None:
    op.drop_index("ix_legislation_alias_lower_alias", table_name="legislation_alias")
    op.drop_index("ix_legislation_alias_legislation_id", table_name="legislation_alias")
    op.drop_table("legislation_alias")
