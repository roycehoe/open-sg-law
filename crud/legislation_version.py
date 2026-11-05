from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from sqlalchemy import update
from sqlmodel import Session, col, func, select

from database.legislation_version import LegislationVersion
from utils.legislation_version_update import LegislationVersionNewestUpdate


@dataclass(frozen=True)
class LegislationVersionRow:
    id: int
    legislation_id: int
    source_response_id: int
    version_date: Optional[date]
    captured_at: datetime
    is_newest: bool


class CRUDLegislationVersion:
    def __init__(self, session: Session):
        self.session = session

    def add_many(self, legislation_versions: list[LegislationVersion]) -> None:
        self.session.add_all(legislation_versions)
        self.session.flush()

    def get_count(self) -> int:
        statement = select(func.count()).select_from(LegislationVersion)
        return self.session.exec(statement).one()

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
