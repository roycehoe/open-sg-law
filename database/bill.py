from datetime import date, datetime
from typing import Optional

from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel


class Bill(SQLModel, table=True):
    __tablename__ = "bill"  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr

    id: Optional[int] = Field(default=None, primary_key=True)

    title: str = Field(sa_column=Column(Text, nullable=False))
    title_key: str = Field(sa_column=Column(Text, nullable=False, index=True))
    first_sitting_date: datetime
    last_sitting_date: datetime

    is_passed: bool


class BillReport(SQLModel, table=True):
    __tablename__ = "bill_report"  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr
    __table_args__ = (
        UniqueConstraint(
            "bill_id",
            "sprs_report_id",
            name="uq_bill_report_bill_id_sprs_report_id",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    sprs_report_id: str = Field(sa_column=Column(Text, nullable=False))
    openhansard_url: str = Field(sa_column=Column(Text, nullable=False))
    report_type: str = Field(sa_column=Column(Text, nullable=False))
    sitting_date: date
    title: str = Field(sa_column=Column(Text, nullable=False))
    hansard_row_id: int

    bill_id: int = Field(foreign_key="bill.id", index=True)
