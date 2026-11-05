import re
from dataclasses import dataclass

from crud.legislation import LegislationRow
from crud.legislation_alias import LegislationAliasRow
from database.legislation_alias import LegislationAlias
from enums import AliasKind

_TITLE_YEAR_PATTERN = re.compile(r"^(.+) \d{4}$")


@dataclass(frozen=True)
class PlannedAlias:
    alias: str
    kind: AliasKind
    legislation_id: int


@dataclass(frozen=True)
class LegislationAliasWrite:
    legislation_aliases_to_insert: list[LegislationAlias]
    legislation_alias_ids_to_delete: list[int]
    unchanged_count: int


def build_planned_aliases(legislation_rows: list[LegislationRow]) -> list[PlannedAlias]:
    planned_aliases: list[PlannedAlias] = []
    for legislation_row in legislation_rows:
        planned_aliases.append(
            PlannedAlias(
                legislation_row.title, AliasKind.FULL_TITLE, legislation_row.id
            )
        )
        match = _TITLE_YEAR_PATTERN.match(legislation_row.title)
        if match is not None:
            planned_aliases.append(
                PlannedAlias(
                    match.group(1), AliasKind.TITLE_WITHOUT_YEAR, legislation_row.id
                )
            )
        planned_aliases.append(
            PlannedAlias(
                legislation_row.sso_code, AliasKind.SSO_CODE, legislation_row.id
            )
        )
    return planned_aliases


def build_legislation_alias_write(
    planned_aliases: list[PlannedAlias],
    legislation_alias_rows: list[LegislationAliasRow],
) -> LegislationAliasWrite:
    planned_alias_key_to_alias = {
        (planned_alias.legislation_id, planned_alias.kind, planned_alias.alias): (
            planned_alias
        )
        for planned_alias in planned_aliases
    }
    stored_alias_key_to_id = {
        (
            legislation_alias_row.legislation_id,
            legislation_alias_row.kind,
            legislation_alias_row.alias,
        ): legislation_alias_row.id
        for legislation_alias_row in legislation_alias_rows
    }
    legislation_aliases_to_insert = [
        LegislationAlias(
            alias=planned_alias.alias,
            kind=planned_alias.kind,
            legislation_id=planned_alias.legislation_id,
        )
        for planned_alias_key, planned_alias in planned_alias_key_to_alias.items()
        if planned_alias_key not in stored_alias_key_to_id
    ]
    return LegislationAliasWrite(
        legislation_aliases_to_insert=legislation_aliases_to_insert,
        legislation_alias_ids_to_delete=[
            legislation_alias_id
            for stored_alias_key, legislation_alias_id in stored_alias_key_to_id.items()
            if stored_alias_key not in planned_alias_key_to_alias
        ],
        unchanged_count=len(planned_alias_key_to_alias)
        - len(legislation_aliases_to_insert),
    )
