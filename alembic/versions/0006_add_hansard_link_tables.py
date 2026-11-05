"""add hansard link tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-05 16:00:00.000000

"""

from typing import Optional, Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: Optional[Union[str, Sequence[str]]] = "0005"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def upgrade() -> None:
    op.create_table(
        "bill",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("title_key", sa.Text(), nullable=False),
        sa.Column("first_sitting_date", sa.DateTime(), nullable=False),
        sa.Column("last_sitting_date", sa.DateTime(), nullable=False),
        sa.Column("is_passed", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bill_title_key", "bill", ["title_key"])
    op.create_table(
        "bill_report",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sprs_report_id", sa.Text(), nullable=False),
        sa.Column("openhansard_url", sa.Text(), nullable=False),
        sa.Column("report_type", sa.Text(), nullable=False),
        sa.Column("sitting_date", sa.Date(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("hansard_row_id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["bill_id"], ["bill.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bill_id",
            "sprs_report_id",
            name="uq_bill_report_bill_id_sprs_report_id",
        ),
    )
    op.create_index("ix_bill_report_bill_id", "bill_report", ["bill_id"])
    op.create_table(
        "act_history_entry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("printed_text", sa.Text(), nullable=False),
        sa.Column("printed_law_number", sa.Text(), nullable=False),
        sa.Column("printed_title", sa.Text(), nullable=False),
        sa.Column("printed_bill_number", sa.Text(), nullable=True),
        sa.Column("first_reading_date", sa.Date(), nullable=True),
        sa.Column("second_reading_date", sa.Date(), nullable=True),
        sa.Column("third_reading_date", sa.Date(), nullable=True),
        sa.Column("commencement_date", sa.Date(), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("bill_link_source", sa.Text(), nullable=True),
        sa.Column("legislation_id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "kind IN ('ACT', 'ORDINANCE', 'REVISED_EDITION', 'SUBSIDIARY_LEGISLATION', 'OTHER')",
            name="ck_act_history_entry_kind",
        ),
        sa.CheckConstraint(
            "bill_link_source IS NULL OR bill_link_source IN ('FIRST_READING_DATE', 'THIRD_READING_DATE', 'SECOND_READING_DATE', 'LOOSE_TITLE_READING_DATES', 'SIMILAR_TITLE_READING_DATES', 'HAND_KEPT')",
            name="ck_act_history_entry_bill_link_source",
        ),
        sa.ForeignKeyConstraint(["bill_id"], ["bill.id"]),
        sa.ForeignKeyConstraint(["legislation_id"], ["legislation.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "legislation_id",
            "ordinal",
            name="uq_act_history_entry_legislation_id_ordinal",
        ),
    )
    op.create_index(
        "ix_act_history_entry_legislation_id", "act_history_entry", ["legislation_id"]
    )
    op.create_index("ix_act_history_entry_bill_id", "act_history_entry", ["bill_id"])


def downgrade() -> None:
    op.drop_index("ix_act_history_entry_bill_id", table_name="act_history_entry")
    op.drop_index("ix_act_history_entry_legislation_id", table_name="act_history_entry")
    op.drop_table("act_history_entry")
    op.drop_index("ix_bill_report_bill_id", table_name="bill_report")
    op.drop_table("bill_report")
    op.drop_index("ix_bill_title_key", table_name="bill")
    op.drop_table("bill")
