from typing import Optional

from sqlalchemy import Column, ForeignKey, Text
from sqlmodel import Field, SQLModel

import database.source  # noqa: F401 registers Source so the foreign key resolves
from enums import SourceName


class Legislation(SQLModel, table=True):
    __tablename__ = "legislation"  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr

    id: Optional[int] = Field(default=None, primary_key=True)

    sso_code: str = Field(sa_column=Column(Text, nullable=False, unique=True))
    title: str = Field(sa_column=Column(Text, nullable=False))

    is_in_newest_listing: bool

    listing_source: SourceName = Field(
        sa_column=Column(Text, ForeignKey("source.name"), nullable=False)
    )
