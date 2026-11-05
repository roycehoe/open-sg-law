from typing import Optional

from sqlalchemy import CheckConstraint, Column, Index, Text, UniqueConstraint, text
from sqlmodel import Field, SQLModel

import database.legislation  # noqa: F401 registers Legislation so the foreign key resolves
from enums import AliasKind


class LegislationAlias(SQLModel, table=True):
    __tablename__ = "legislation_alias"  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr
    __table_args__ = (
        UniqueConstraint(
            "legislation_id", "kind", name="uq_legislation_alias_legislation_id_kind"
        ),
        CheckConstraint(
            "kind IN ("
            + ", ".join(f"'{alias_kind.value}'" for alias_kind in AliasKind)
            + ")",
            name="ck_legislation_alias_kind",
        ),
        Index("ix_legislation_alias_lower_alias", text("lower(alias)")),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    alias: str = Field(sa_column=Column(Text, nullable=False))

    kind: AliasKind = Field(sa_column=Column(Text, nullable=False))

    legislation_id: int = Field(foreign_key="legislation.id", index=True)
