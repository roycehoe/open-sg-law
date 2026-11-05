from datetime import date, datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlmodel import Field, SQLModel

import database.legislation  # noqa: F401 registers Legislation so the foreign key resolves
import database.source  # noqa: F401 registers Source so the foreign key resolves
import database.source_response  # noqa: F401 registers SourceResponse so the foreign key resolves
from enums import SourceName


class LegislationVersion(SQLModel, table=True):
    __tablename__ = "legislation_version"  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr

    id: Optional[int] = Field(default=None, primary_key=True)

    printed_version_date: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    version_date: Optional[date] = None
    version_stamp: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    archive_timestamp: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    archive_digest: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    body_character_count: Optional[int] = None
    section_character_count: Optional[int] = None

    captured_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    is_newest: bool

    source: SourceName = Field(
        sa_column=Column(Text, ForeignKey("source.name"), nullable=False)
    )
    legislation_id: int = Field(foreign_key="legislation.id", index=True)
    source_response_id: int = Field(
        sa_column=Column(
            Integer, ForeignKey("source_response.id"), nullable=False, unique=True
        )
    )
