from typing import Optional

from sqlmodel import Session, col, select

from database.source import Source
from enums import SourceName


class CRUDSource:
    def __init__(self, session: Session):
        self.session = session

    def get_all(self) -> list[Source]:
        statement = select(Source).order_by(col(Source.id))
        return list(self.session.exec(statement).all())

    # NOTE: populate_existing, because a locked read of a row already in the session would keep its stale state
    def get_all_for_update(self) -> list[Source]:
        statement = (
            select(Source)
            .order_by(col(Source.id))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return list(self.session.exec(statement).all())

    def get_by_name(self, name: SourceName) -> Optional[Source]:
        statement = select(Source).where(Source.name == name)
        return self.session.exec(statement).first()

    # NOTE: populate_existing, because a locked read of a row already in the session would keep its stale state
    def get_by_name_for_update(self, name: SourceName) -> Optional[Source]:
        statement = (
            select(Source)
            .where(Source.name == name)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return self.session.exec(statement).first()

    def update(self, source: Source) -> None:
        self.session.add(source)
        self.session.flush()
