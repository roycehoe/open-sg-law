from dataclasses import dataclass

from sqlmodel import Session, col, delete, func, select

from database.legislation_alias import LegislationAlias
from enums import AliasKind


@dataclass(frozen=True)
class LegislationAliasRow:
    id: int
    alias: str
    kind: AliasKind
    legislation_id: int


class CRUDLegislationAlias:
    def __init__(self, session: Session):
        self.session = session

    def add_many(self, legislation_aliases: list[LegislationAlias]) -> None:
        self.session.add_all(legislation_aliases)
        self.session.flush()

    def get_count(self) -> int:
        statement = select(func.count()).select_from(LegislationAlias)
        return self.session.exec(statement).one()

    def get_rows(self) -> list[LegislationAliasRow]:
        statement = select(
            LegislationAlias.id,
            LegislationAlias.alias,
            LegislationAlias.kind,
            LegislationAlias.legislation_id,
        ).order_by(col(LegislationAlias.legislation_id), col(LegislationAlias.kind))
        return [
            LegislationAliasRow(*row)  # pyright: ignore[reportArgumentType] a stored row has an id
            for row in self.session.exec(statement).all()
        ]

    def delete_by_ids(self, legislation_alias_ids: list[int]) -> None:
        statement = delete(LegislationAlias).where(
            col(LegislationAlias.id).in_(legislation_alias_ids)
        )
        self.session.execute(statement)
        self.session.flush()
