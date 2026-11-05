from dataclasses import dataclass

from sqlalchemy import update
from sqlmodel import Session, func, select

from database.legislation import Legislation
from enums import SourceName
from utils.legislation_update import LegislationUpdate


@dataclass(frozen=True)
class LegislationRow:
    id: int
    sso_code: str
    title: str
    is_in_newest_listing: bool
    listing_source: SourceName


class CRUDLegislation:
    def __init__(self, session: Session):
        self.session = session

    def add_many(self, legislations: list[Legislation]) -> None:
        self.session.add_all(legislations)
        self.session.flush()

    def get_count(self) -> int:
        statement = select(func.count()).select_from(Legislation)
        return self.session.exec(statement).one()

    def get_rows(self) -> list[LegislationRow]:
        statement = select(  # pyright: ignore[reportCallIssue] sqlmodel types select for at most four columns
            Legislation.id,
            Legislation.sso_code,
            Legislation.title,
            Legislation.is_in_newest_listing,
            Legislation.listing_source,
        ).order_by(Legislation.sso_code)
        return [LegislationRow(*row) for row in self.session.exec(statement).all()]

    def update_many(self, legislation_updates: list[LegislationUpdate]) -> None:
        if not legislation_updates:
            return

        self.session.execute(
            update(Legislation),
            [
                {
                    "id": legislation_update.id,
                    "title": legislation_update.title,
                    "is_in_newest_listing": legislation_update.is_in_newest_listing,
                    "listing_source": legislation_update.listing_source,
                }
                for legislation_update in legislation_updates
            ],
        )
