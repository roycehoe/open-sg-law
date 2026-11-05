"""add legislation section number index

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-05 21:00:00.000000

"""

from typing import Optional, Sequence, Union

from alembic import op

revision: str = "0011"
down_revision: Optional[Union[str, Sequence[str]]] = "0010"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_legislation_section_legislation_version_id_printed_number",
        "legislation_section",
        ["legislation_version_id", "printed_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_legislation_section_legislation_version_id_printed_number",
        "legislation_section",
        type_="unique",
    )
