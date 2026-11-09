from datetime import date
from typing import Optional

from sqlalchemy import CheckConstraint, Column, Date, Text, UniqueConstraint
from sqlmodel import Field, SQLModel

import database.source_response  # noqa: F401 registers SourceResponse so the foreign key resolves
from enums import JudgmentBlockKind


class Judgment(SQLModel, table=True):
    __tablename__ = "judgment"  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr
    __table_args__ = (
        UniqueConstraint("elitigation_url", name="uq_judgment_elitigation_url"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    elitigation_url: str = Field(sa_column=Column(Text, nullable=False))
    neutral_citation: str = Field(sa_column=Column(Text, nullable=False, index=True))
    case_name: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    printed_court: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    printed_case_number: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    printed_coram: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    printed_counsel: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    printed_catchwords: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    printed_decision_date: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    decision_date: Optional[date] = Field(
        default=None, sa_column=Column(Date, nullable=True)
    )
    body_character_count: int
    block_character_count: int

    source_response_id: int = Field(foreign_key="source_response.id")


class JudgmentBlock(SQLModel, table=True):
    __tablename__ = "judgment_block"  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr
    __table_args__ = (
        UniqueConstraint(
            "judgment_id", "ordinal", name="uq_judgment_block_judgment_id_ordinal"
        ),
        CheckConstraint(
            "kind IN ("
            + ", ".join(f"'{block_kind.value}'" for block_kind in JudgmentBlockKind)
            + ")",
            name="ck_judgment_block_kind",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    ordinal: int
    printed_number: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    text: str = Field(sa_column=Column(Text, nullable=False))
    source_style: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    kind: JudgmentBlockKind = Field(sa_column=Column(Text, nullable=False))

    judgment_id: int = Field(foreign_key="judgment.id", index=True)
