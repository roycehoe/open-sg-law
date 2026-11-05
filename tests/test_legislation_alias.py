from sqlmodel import Session

from crud.legislation import CRUDLegislation, LegislationRow
from crud.legislation_alias import CRUDLegislationAlias
from enums import AliasKind, SourceName
from populate.legislation_aliases import (
    get_legislation_alias_write,
    write_legislation_aliases,
)
from services.legislation_alias import PlannedAlias, build_planned_aliases
from tests.document_seed import seed_legislation
from tests.listing_seed import seed_archive_legislation
from tests.source_seed import seed_sources
from utils.legislation_update import LegislationUpdate

_DATED_TITLE_ALIAS_COUNT = 18


def test_a_dated_title_gives_three_aliases_and_an_undated_title_two() -> None:
    legislation_rows = [
        LegislationRow(
            id=1,
            sso_code="AA2004",
            title="Accountants Act 2004",
            is_in_newest_listing=True,
            listing_source=SourceName.SSO,
        ),
        LegislationRow(
            id=2,
            sso_code="CONS1963",
            title="Constitution of the Republic of Singapore",
            is_in_newest_listing=True,
            listing_source=SourceName.SSO,
        ),
    ]

    assert build_planned_aliases(legislation_rows) == [
        PlannedAlias("Accountants Act 2004", AliasKind.FULL_TITLE, 1),
        PlannedAlias("Accountants Act", AliasKind.TITLE_WITHOUT_YEAR, 1),
        PlannedAlias("AA2004", AliasKind.SSO_CODE, 1),
        PlannedAlias(
            "Constitution of the Republic of Singapore", AliasKind.FULL_TITLE, 2
        ),
        PlannedAlias("CONS1963", AliasKind.SSO_CODE, 2),
    ]


def test_the_stage_plans_every_alias_once_and_nothing_after_the_write(
    scratch_session: Session,
) -> None:
    seed_archive_legislation(scratch_session)

    legislation_alias_write = get_legislation_alias_write(scratch_session)
    write_legislation_aliases(scratch_session, legislation_alias_write)
    scratch_session.commit()
    second_legislation_alias_write = get_legislation_alias_write(scratch_session)

    assert (
        len(legislation_alias_write.legislation_aliases_to_insert)
        == _DATED_TITLE_ALIAS_COUNT
    )
    assert legislation_alias_write.legislation_alias_ids_to_delete == []
    assert legislation_alias_write.unchanged_count == 0
    assert second_legislation_alias_write.legislation_aliases_to_insert == []
    assert second_legislation_alias_write.legislation_alias_ids_to_delete == []
    assert second_legislation_alias_write.unchanged_count == _DATED_TITLE_ALIAS_COUNT
    assert CRUDLegislationAlias(scratch_session).get_count() == _DATED_TITLE_ALIAS_COUNT


def test_a_changed_title_replaces_its_title_aliases(scratch_session: Session) -> None:
    seed_sources(scratch_session)
    seed_legislation(scratch_session, {"AA2004": "Accountants Act"})
    write_legislation_aliases(
        scratch_session, get_legislation_alias_write(scratch_session)
    )
    scratch_session.commit()
    stored_alias_rows = CRUDLegislationAlias(scratch_session).get_rows()
    legislation_row = CRUDLegislation(scratch_session).get_rows()[0]
    CRUDLegislation(scratch_session).update_many(
        [
            LegislationUpdate(
                id=legislation_row.id,
                title="Accountants Act 2004",
                is_in_newest_listing=legislation_row.is_in_newest_listing,
                listing_source=legislation_row.listing_source,
            )
        ]
    )

    legislation_alias_write = get_legislation_alias_write(scratch_session)
    write_legislation_aliases(scratch_session, legislation_alias_write)

    assert legislation_alias_write.legislation_alias_ids_to_delete == [
        stored_alias_row.id
        for stored_alias_row in stored_alias_rows
        if stored_alias_row.kind == AliasKind.FULL_TITLE
    ]
    assert legislation_alias_write.unchanged_count == 1
    assert [
        (legislation_alias_row.alias, legislation_alias_row.kind)
        for legislation_alias_row in CRUDLegislationAlias(scratch_session).get_rows()
    ] == [
        ("Accountants Act 2004", AliasKind.FULL_TITLE),
        ("AA2004", AliasKind.SSO_CODE),
        ("Accountants Act", AliasKind.TITLE_WITHOUT_YEAR),
    ]
