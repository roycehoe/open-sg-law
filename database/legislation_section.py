from typing import Optional

from sqlalchemy import CheckConstraint, Column, Computed, Index, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlmodel import Field, SQLModel

import database.legislation_version  # noqa: F401 registers LegislationVersion so the foreign key resolves
from enums import LegislationSectionKind


class LegislationSection(SQLModel, table=True):
    __tablename__ = "legislation_section"  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr
    __table_args__ = (
        UniqueConstraint(
            "legislation_version_id",
            "ordinal",
            name="uq_legislation_section_legislation_version_id_ordinal",
        ),
        UniqueConstraint(
            "legislation_version_id",
            "printed_number",
            name="uq_legislation_section_legislation_version_id_printed_number",
        ),
        CheckConstraint(
            "kind IN ("
            + ", ".join(
                f"'{section_kind.value}'" for section_kind in LegislationSectionKind
            )
            + ")",
            name="ck_legislation_section_kind",
        ),
        Index(
            "ix_legislation_section_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    ordinal: int
    printed_number: str = Field(sa_column=Column(Text, nullable=False))
    heading: Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    part_heading: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    division_heading: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    text: str = Field(sa_column=Column(Text, nullable=False))
    first_page_number: int
    last_page_number: int
    sso_anchor: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    search_vector: Optional[str] = Field(
        default=None,
        sa_column=Column(
            TSVECTOR,
            Computed(
                """to_tsvector('english'::regconfig, coalesce(heading, '') || ' ' || "text")""",
                persisted=True,
            ),
        ),
    )

    kind: LegislationSectionKind = Field(sa_column=Column(Text, nullable=False))
    is_repealed: bool
    is_on_image_page: bool

    legislation_version_id: int = Field(
        foreign_key="legislation_version.id", index=True
    )
