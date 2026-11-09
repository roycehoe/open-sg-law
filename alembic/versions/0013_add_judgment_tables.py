"""add judgment tables

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-09 12:00:00.000000

"""

from typing import Optional, Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: Optional[Union[str, Sequence[str]]] = "0012"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None

_SITE_ROLE_NAME = "open_sg_law_site"
_PUBLIC_SCHEMA = "public"
_PUBLISHED = "PUBLISHED"
_NEW_TABLE_NAMES = ("judgment", "judgment_block")
_NEW_TABLE_SOURCE_NAME = "ELITIGATION"
TABLE_NAME_TO_SOURCE_NAMES = (
    ("source", ()),
    ("legislation", ("SSO", "INTERNET_ARCHIVE")),
    ("legislation_version", ("SSO", "INTERNET_ARCHIVE")),
    ("legislation_section", ("SSO", "INTERNET_ARCHIVE")),
    ("legislation_alias", ("SSO", "INTERNET_ARCHIVE")),
    ("bill", ("OPENHANSARD_LINKS",)),
    ("bill_report", ("OPENHANSARD_LINKS",)),
    ("act_history_entry", ("OPENHANSARD_LINKS", "SSO")),
    ("judgment", ("ELITIGATION",)),
    ("judgment_block", ("ELITIGATION",)),
)


def upgrade() -> None:
    op.create_table(
        "judgment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("elitigation_url", sa.Text(), nullable=False),
        sa.Column("neutral_citation", sa.Text(), nullable=False),
        sa.Column("case_name", sa.Text(), nullable=True),
        sa.Column("printed_court", sa.Text(), nullable=True),
        sa.Column("printed_case_number", sa.Text(), nullable=True),
        sa.Column("printed_coram", sa.Text(), nullable=True),
        sa.Column("printed_counsel", sa.Text(), nullable=True),
        sa.Column("printed_catchwords", sa.Text(), nullable=True),
        sa.Column("printed_decision_date", sa.Text(), nullable=True),
        sa.Column("decision_date", sa.Date(), nullable=True),
        sa.Column("body_character_count", sa.Integer(), nullable=False),
        sa.Column("block_character_count", sa.Integer(), nullable=False),
        sa.Column("source_response_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["source_response_id"], ["source_response.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("elitigation_url", name="uq_judgment_elitigation_url"),
    )
    op.create_index("ix_judgment_neutral_citation", "judgment", ["neutral_citation"])
    op.create_table(
        "judgment_block",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("printed_number", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_style", sa.Text(), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("judgment_id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('FRONT_MATTER', 'HEADING', 'PARAGRAPH', 'QUOTE', 'LIST', 'TABLE', 'FOOTNOTE', 'SIGN_OFF', 'COUNSEL', 'PLAIN')",
            name="ck_judgment_block_kind",
        ),
        sa.ForeignKeyConstraint(["judgment_id"], ["judgment.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "judgment_id", "ordinal", name="uq_judgment_block_judgment_id_ordinal"
        ),
    )
    op.create_index(
        "ix_judgment_block_judgment_id", "judgment_block", ["judgment_id"]
    )
    connection = op.get_bind()
    is_published = (
        connection.execute(
            sa.text("SELECT publish_status FROM source WHERE name = :name"),
            {"name": _NEW_TABLE_SOURCE_NAME},
        ).scalar_one_or_none()
        == _PUBLISHED
    )
    if not is_published:
        return
    identifier_preparer = connection.dialect.identifier_preparer
    for table_name in _NEW_TABLE_NAMES:
        op.execute(
            f"GRANT SELECT ON TABLE {identifier_preparer.quote(_PUBLIC_SCHEMA)}.{identifier_preparer.quote(table_name)} TO {identifier_preparer.quote(_SITE_ROLE_NAME)}"
        )


def downgrade() -> None:
    op.drop_index("ix_judgment_block_judgment_id", table_name="judgment_block")
    op.drop_table("judgment_block")
    op.drop_index("ix_judgment_neutral_citation", table_name="judgment")
    op.drop_table("judgment")
