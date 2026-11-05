from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    Text,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel

import database.harvest_run  # noqa: F401 registers HarvestRun so the foreign key resolves
import database.source  # noqa: F401 registers Source so the foreign key resolves
from enums import ResponseKind, SourceName


def _get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SourceResponse(SQLModel, table=True):
    __tablename__ = "source_response"  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr
    __table_args__ = (
        CheckConstraint(
            "kind IN ("
            + ", ".join(f"'{response_kind.value}'" for response_kind in ResponseKind)
            + ")",
            name="ck_source_response_kind",
        ),
        CheckConstraint(
            "(body_text IS NULL) <> (body_bytes IS NULL)",
            name="ck_source_response_one_body",
        ),
        UniqueConstraint(
            "requested_url", "sha256", name="uq_source_response_requested_url_sha256"
        ),
        Index("ix_source_response_source_kind", "source", "kind"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    requested_url: str = Field(sa_column=Column(Text, nullable=False))
    final_url: str = Field(sa_column=Column(Text, nullable=False))
    status_code: int
    content_type: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    body_text: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    body_bytes: Optional[bytes] = Field(
        default=None, sa_column=Column(LargeBinary, nullable=True)
    )
    sha256: str = Field(sa_column=Column(Text, nullable=False))
    byte_length: int

    fetched_at: datetime = Field(
        default_factory=_get_utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    kind: ResponseKind = Field(sa_column=Column(Text, nullable=False))

    source: SourceName = Field(
        sa_column=Column(Text, ForeignKey("source.name"), nullable=False)
    )
    harvest_run_id: int = Field(foreign_key="harvest_run.id", index=True)
