from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, col, delete, func, select

from database.legislation_section import LegislationSection
from enums import LegislationSectionKind


@dataclass(frozen=True)
class LegislationSectionRow:
    ordinal: int
    printed_number: str
    heading: Optional[str]
    part_heading: Optional[str]
    division_heading: Optional[str]
    text: str
    first_page_number: int
    last_page_number: int
    sso_anchor: Optional[str]
    kind: LegislationSectionKind
    is_repealed: bool
    is_on_image_page: bool


class CRUDLegislationSection:
    def __init__(self, session: Session):
        self.session = session

    def add_many(self, legislation_sections: list[LegislationSection]) -> None:
        self.session.add_all(legislation_sections)
        self.session.flush()

    def get_count(self) -> int:
        statement = select(func.count()).select_from(LegislationSection)
        return self.session.exec(statement).one()

    def get_count_by_legislation_version_id(self, legislation_version_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(LegislationSection)
            .where(
                col(LegislationSection.legislation_version_id) == legislation_version_id
            )
        )
        return self.session.exec(statement).one()

    def get_rows_by_legislation_version_id(
        self, legislation_version_id: int
    ) -> list[LegislationSectionRow]:
        statement = (
            select(  # pyright: ignore[reportCallIssue] sqlmodel types select for at most four columns
                LegislationSection.ordinal,
                LegislationSection.printed_number,
                LegislationSection.heading,
                LegislationSection.part_heading,
                LegislationSection.division_heading,
                LegislationSection.text,
                LegislationSection.first_page_number,
                LegislationSection.last_page_number,
                LegislationSection.sso_anchor,
                LegislationSection.kind,
                LegislationSection.is_repealed,
                LegislationSection.is_on_image_page,
            )
            .where(
                col(LegislationSection.legislation_version_id) == legislation_version_id
            )
            .order_by(LegislationSection.ordinal)
        )
        return [
            LegislationSectionRow(*row) for row in self.session.exec(statement).all()
        ]

    def delete_by_legislation_version_id(self, legislation_version_id: int) -> None:
        statement = delete(LegislationSection).where(
            col(LegislationSection.legislation_version_id) == legislation_version_id
        )
        self.session.execute(statement)
        self.session.flush()
