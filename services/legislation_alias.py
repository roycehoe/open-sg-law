import re
from dataclasses import dataclass

from crud.legislation import LegislationRow
from enums import AliasKind

_TITLE_YEAR_PATTERN = re.compile(r"^(.+) \d{4}$")


@dataclass(frozen=True)
class PlannedAlias:
    alias: str
    kind: AliasKind
    legislation_id: int


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
