from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Text
from sqlmodel import Field, SQLModel

import database.source  # noqa: F401 registers Source so the foreign key resolves
from enums import HarvestRunStatus, SourceName


def _get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HarvestRun(SQLModel, table=True):
    __tablename__ = "harvest_run"  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr
    __table_args__ = (
        CheckConstraint(
            "status IN ("
            + ", ".join(f"'{status.value}'" for status in HarvestRunStatus)
            + ")",
            name="ck_harvest_run_status",
        ),
        Index("ix_harvest_run_source_started_at", "source", "started_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    requests_sent: int = 0
    bodies_stored: int = 0
    bodies_unchanged: int = 0
    failures: int = 0
    halt_reason: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    failure_reason: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    started_at: datetime = Field(
        default_factory=_get_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    finished_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    status: HarvestRunStatus = Field(
        default=HarvestRunStatus.RUNNING, sa_column=Column(Text, nullable=False)
    )

    source: SourceName = Field(
        sa_column=Column(Text, ForeignKey("source.name"), nullable=False)
    )
