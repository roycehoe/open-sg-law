from datetime import date
from typing import Optional

from sqlalchemy import CheckConstraint, Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

import database.bill  # noqa: F401 registers Bill so the foreign key resolves
import database.legislation  # noqa: F401 registers Legislation so the foreign key resolves
from enums import ActHistoryEntryKind, BillLinkSource


class ActHistoryEntry(SQLModel, table=True):
    __tablename__ = "act_history_entry"  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr
    __table_args__ = (
        UniqueConstraint(
            "legislation_id",
            "ordinal",
            name="uq_act_history_entry_legislation_id_ordinal",
        ),
        CheckConstraint(
            "kind IN ("
            + ", ".join(f"'{entry_kind.value}'" for entry_kind in ActHistoryEntryKind)
            + ")",
            name="ck_act_history_entry_kind",
        ),
        CheckConstraint(
            "bill_link_source IS NULL OR bill_link_source IN ("
            + ", ".join(f"'{link_source.value}'" for link_source in BillLinkSource)
            + ")",
            name="ck_act_history_entry_bill_link_source",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    ordinal: int
    printed_text: str = Field(sa_column=Column(Text, nullable=False))
    printed_law_number: str = Field(sa_column=Column(Text, nullable=False))
    printed_title: str = Field(sa_column=Column(Text, nullable=False))
    printed_bill_number: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    first_reading_date: Optional[date] = None
    second_reading_date: Optional[date] = None
    third_reading_date: Optional[date] = None
    commencement_date: Optional[date] = None

    kind: ActHistoryEntryKind = Field(sa_column=Column(Text, nullable=False))
    bill_link_source: Optional[BillLinkSource] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    legislation_id: int = Field(foreign_key="legislation.id", index=True)
    bill_id: Optional[int] = Field(default=None, foreign_key="bill.id", index=True)
