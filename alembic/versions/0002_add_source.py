"""add source

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05 13:30:00.000000

"""

from typing import Optional, Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: Optional[Union[str, Sequence[str]]] = "0001"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None

SOURCE_ROWS = (
    {"name": "SSO", "publish_status": "PUBLISHED", "sso_access_state": "UNTESTED"},
    {
        "name": "INTERNET_ARCHIVE",
        "publish_status": "PUBLISHED",
        "sso_access_state": None,
    },
    {"name": "EGAZETTE", "publish_status": "PUBLISHED", "sso_access_state": None},
    {"name": "DATA_GOV_SG", "publish_status": "PUBLISHED", "sso_access_state": None},
    {"name": "ELITIGATION", "publish_status": "UNPUBLISHED", "sso_access_state": None},
    {
        "name": "OPENHANSARD_LINKS",
        "publish_status": "PUBLISHED",
        "sso_access_state": None,
    },
)


def upgrade() -> None:
    source_table = op.create_table(
        "source",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("publish_status_reason", sa.Text(), nullable=True),
        sa.Column("sso_access_state_reason", sa.Text(), nullable=True),
        sa.Column(
            "publish_status_changed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "sso_access_state_changed_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("publish_status", sa.Text(), nullable=False),
        sa.Column("sso_access_state", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "name IN ('SSO', 'INTERNET_ARCHIVE', 'EGAZETTE', 'DATA_GOV_SG', 'ELITIGATION', 'OPENHANSARD_LINKS')",
            name="ck_source_name",
        ),
        sa.CheckConstraint(
            "publish_status IN ('PUBLISHED', 'UNPUBLISHED')",
            name="ck_source_publish_status",
        ),
        sa.CheckConstraint(
            "sso_access_state IS NULL OR sso_access_state IN ('UNTESTED', 'SERVING', 'CHALLENGED')",
            name="ck_source_sso_access_state",
        ),
        sa.CheckConstraint(
            "(name = 'SSO') = (sso_access_state IS NOT NULL)",
            name="ck_source_sso_access_state_only_on_sso",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.bulk_insert(source_table, list(SOURCE_ROWS))


def downgrade() -> None:
    op.drop_table("source")
