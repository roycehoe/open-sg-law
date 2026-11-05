from sqlmodel import Session

from crud.legislation import CRUDLegislation
from crud.legislation_alias import CRUDLegislationAlias
from services.legislation_alias import (
    LegislationAliasWrite,
    build_legislation_alias_write,
    build_planned_aliases,
)


def get_legislation_alias_write(session: Session) -> LegislationAliasWrite:
    return build_legislation_alias_write(
        build_planned_aliases(CRUDLegislation(session).get_rows()),
        CRUDLegislationAlias(session).get_rows(),
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
