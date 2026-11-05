"""empty first revision

Revision ID: 0001
Revises:
Create Date: 2026-11-05 12:00:00.000000

"""

from typing import Optional, Sequence, Union

revision: str = "0001"
down_revision: Optional[Union[str, Sequence[str]]] = None
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
