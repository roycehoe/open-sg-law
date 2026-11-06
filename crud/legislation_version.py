from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Integer, cast, extract, update
from sqlmodel import Session, col, func, select

from database.legislation import Legislation
from database.legislation_version import LegislationVersion
from enums import SourceName
from utils.legislation_version_update import LegislationVersionNewestUpdate


@dataclass(frozen=True)
class LegislationVersionRow:
    id: int
    legislation_id: int
    source_response_id: int
    version_date: Optional[date]
    captured_at: datetime
    is_newest: bool


@dataclass(frozen=True)
class VersionDocumentRow:
    id: int
    sso_code: str
    source_response_id: int


@dataclass(frozen=True)
class SourceCountRow:
    source: SourceName
    legislation_count: int


@dataclass(frozen=True)
class VersionYearCountRow:
    version_year: Optional[int]
    version_count: int


@dataclass(frozen=True)
class CharacterCountRow:
    sso_code: str
    body_character_count: int
    section_character_count: int


class CRUDLegislationVersion:
    def __init__(self, session: Session):
        self.session = session

    def add_many(self, legislation_versions: list[LegislationVersion]) -> None:
        self.session.add_all(legislation_versions)
        self.session.flush()

    def get_count(self) -> int:
        statement = select(func.count()).select_from(LegislationVersion)
        return self.session.exec(statement).one()

    def get_count_by_body_character_count_null(self) -> int:
        statement = (
            select(func.count())
            .select_from(LegislationVersion)
            .where(col(LegislationVersion.body_character_count).is_(None))
        )
        return self.session.exec(statement).one()

    def get_count_by_is_newest_and_section_character_count_not_null_and_legislation_is_in_newest_listing(
        self, is_newest: bool, is_in_newest_listing: bool
    ) -> int:
        statement = (
            select(func.count())
            .select_from(LegislationVersion)
            .join(Legislation, col(Legislation.id) == LegislationVersion.legislation_id)
            .where(col(LegislationVersion.is_newest).is_(is_newest))
            .where(col(LegislationVersion.section_character_count).is_not(None))
            .where(col(Legislation.is_in_newest_listing).is_(is_in_newest_listing))
        )
        return self.session.exec(statement).one()

    def get_legislation_counts_by_source(self) -> list[SourceCountRow]:
        statement = (
            select(
                LegislationVersion.source,
                func.count(func.distinct(LegislationVersion.legislation_id)),
            )
            .group_by(LegislationVersion.source)
            .order_by(LegislationVersion.source)
        )
        return [
            SourceCountRow(SourceName(source), legislation_count)
            for source, legislation_count in self.session.exec(statement).all()
        ]

    def get_version_year_counts_by_is_newest(
        self, is_newest: bool
    ) -> list[VersionYearCountRow]:
        version_year = cast(
            extract("year", col(LegislationVersion.version_date)), Integer
        )
        statement = (
            select(version_year, func.count())
            .where(col(LegislationVersion.is_newest).is_(is_newest))
            .group_by(version_year)
            .order_by(version_year)
        )
        return [VersionYearCountRow(*row) for row in self.session.exec(statement).all()]

    def get_character_count_rows_by_body_character_count_not_null_and_section_character_count_not_null(
        self,
    ) -> list[CharacterCountRow]:
        statement = (
            select(
                Legislation.sso_code,
                LegislationVersion.body_character_count,
                LegislationVersion.section_character_count,
            )
            .join(Legislation, col(Legislation.id) == LegislationVersion.legislation_id)
            .where(col(LegislationVersion.body_character_count).is_not(None))
            .where(col(LegislationVersion.section_character_count).is_not(None))
            .order_by(Legislation.sso_code, col(LegislationVersion.id))
        )
        return [
            CharacterCountRow(*row)  # pyright: ignore[reportArgumentType] the where clauses leave no NULL count
            for row in self.session.exec(statement).all()
        ]

    def get_rows(self) -> list[LegislationVersionRow]:
        statement = select(  # pyright: ignore[reportCallIssue] sqlmodel types select for at most four columns
            LegislationVersion.id,
            LegislationVersion.legislation_id,
            LegislationVersion.source_response_id,
            LegislationVersion.version_date,
            LegislationVersion.captured_at,
            LegislationVersion.is_newest,
        ).order_by(LegislationVersion.legislation_id, LegislationVersion.id)
        return [
            LegislationVersionRow(*row) for row in self.session.exec(statement).all()
        ]

    def get_version_document_rows(self) -> list[VersionDocumentRow]:
        statement = (
            select(
                LegislationVersion.id,
                Legislation.sso_code,
                LegislationVersion.source_response_id,
            )
            .join(Legislation, col(Legislation.id) == LegislationVersion.legislation_id)
            .order_by(Legislation.sso_code, col(LegislationVersion.id))
        )
        return [
            VersionDocumentRow(*row)  # pyright: ignore[reportArgumentType] a stored row has an id
            for row in self.session.exec(statement).all()
        ]

    def set_is_newest_bulk(
        self,
        legislation_version_newest_updates: list[LegislationVersionNewestUpdate],
    ) -> int:
        if not legislation_version_newest_updates:
            return 0

        self.session.execute(
            update(LegislationVersion),
            [
                {
                    "id": legislation_version_newest_update.id,
                    "is_newest": legislation_version_newest_update.is_newest,
                }
                for legislation_version_newest_update in legislation_version_newest_updates
            ],
        )
        return len(legislation_version_newest_updates)

    def update_character_counts(
        self,
        legislation_version_id: int,
        body_character_count: int,
        section_character_count: int,
    ) -> None:
        statement = (
            update(LegislationVersion)
            .where(col(LegislationVersion.id) == legislation_version_id)
            .values(
                body_character_count=body_character_count,
                section_character_count=section_character_count,
            )
        )
        self.session.execute(statement)
        self.session.flush()
