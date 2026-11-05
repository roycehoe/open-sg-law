"""add legislation section search vector

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-05 20:00:00.000000

"""

from typing import Optional, Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0009"
down_revision: Optional[Union[str, Sequence[str]]] = "0008"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.add_column(
        "legislation_section",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed(
                """to_tsvector('english'::regconfig, coalesce(heading, '') || ' ' || "text")""",
                persisted=True,
            ),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_legislation_section_search_vector",
        "legislation_section",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_legislation_section_search_vector",
        table_name="legislation_section",
    )
    op.drop_column("legislation_section", "search_vector")
