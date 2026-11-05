from dataclasses import dataclass

from sqlmodel import Session

from crud.legislation import CRUDLegislation
from crud.legislation_alias import CRUDLegislationAlias
from database.legislation_alias import LegislationAlias
from services.legislation_alias import build_planned_aliases


@dataclass(frozen=True)
class LegislationAliasWrite:
    legislation_aliases_to_insert: list[LegislationAlias]
    legislation_alias_ids_to_delete: list[int]
    unchanged_count: int


def get_legislation_alias_write(session: Session) -> LegislationAliasWrite:
    planned_aliases = build_planned_aliases(CRUDLegislation(session).get_rows())
    planned_alias_keys = frozenset(
        (planned_alias.legislation_id, planned_alias.kind, planned_alias.alias)
        for planned_alias in planned_aliases
    )
    stored_alias_key_to_id = {
        (
            legislation_alias_row.legislation_id,
            legislation_alias_row.kind,
            legislation_alias_row.alias,
        ): legislation_alias_row.id
        for legislation_alias_row in CRUDLegislationAlias(session).get_rows()
    }
    legislation_aliases_to_insert = [
        LegislationAlias(
            alias=planned_alias.alias,
            kind=planned_alias.kind,
            legislation_id=planned_alias.legislation_id,
        )
        for planned_alias in planned_aliases
        if (planned_alias.legislation_id, planned_alias.kind, planned_alias.alias)
        not in stored_alias_key_to_id
    ]
    return LegislationAliasWrite(
        legislation_aliases_to_insert=legislation_aliases_to_insert,
        legislation_alias_ids_to_delete=[
            legislation_alias_id
            for stored_alias_key, legislation_alias_id in stored_alias_key_to_id.items()
            if stored_alias_key not in planned_alias_keys
        ],
        unchanged_count=len(planned_aliases) - len(legislation_aliases_to_insert),
    )


def write_legislation_aliases(
    session: Session, legislation_alias_write: LegislationAliasWrite
) -> None:
    CRUDLegislationAlias(session).delete_by_ids(
        legislation_alias_write.legislation_alias_ids_to_delete
    )
    CRUDLegislationAlias(session).add_many(
        legislation_alias_write.legislation_aliases_to_insert
    )
