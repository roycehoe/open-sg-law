import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from crud.legislation_alias import CRUDLegislationAlias, LegislationAliasRow
from database.legislation import Legislation
from database.legislation_alias import LegislationAlias
from enums import AliasKind
from tests.document_seed import seed_version_inputs


def _seed_legislation_id(session: Session) -> int:
    seed_version_inputs(session)
    legislation_id = session.exec(select(Legislation.id)).one()
    assert legislation_id is not None
    return legislation_id


def _build_aliases(legislation_id: int) -> list[LegislationAlias]:
    return [
        LegislationAlias(
            alias="Interpretation Act 1965",
            kind=AliasKind.FULL_TITLE,
            legislation_id=legislation_id,
        ),
        LegislationAlias(
            alias="Interpretation Act",
            kind=AliasKind.TITLE_WITHOUT_YEAR,
            legislation_id=legislation_id,
        ),
        LegislationAlias(
            alias="IA1965", kind=AliasKind.SSO_CODE, legislation_id=legislation_id
        ),
    ]


def test_aliases_are_read_back_by_kind(scratch_session: Session) -> None:
    legislation_id = _seed_legislation_id(scratch_session)

    CRUDLegislationAlias(scratch_session).add_many(_build_aliases(legislation_id))

    assert CRUDLegislationAlias(scratch_session).get_rows() == [
        LegislationAliasRow(
            1, "Interpretation Act 1965", AliasKind.FULL_TITLE, legislation_id
        ),
        LegislationAliasRow(3, "IA1965", AliasKind.SSO_CODE, legislation_id),
        LegislationAliasRow(
            2, "Interpretation Act", AliasKind.TITLE_WITHOUT_YEAR, legislation_id
        ),
    ]


def test_a_second_alias_of_one_kind_is_refused(scratch_session: Session) -> None:
    legislation_id = _seed_legislation_id(scratch_session)
    CRUDLegislationAlias(scratch_session).add_many(_build_aliases(legislation_id))

    with pytest.raises(IntegrityError):
        CRUDLegislationAlias(scratch_session).add_many(
            [
                LegislationAlias(
                    alias="Interpretation Act 1965",
                    kind=AliasKind.FULL_TITLE,
                    legislation_id=legislation_id,
                )
            ]
        )


def test_deleting_an_alias_by_id_leaves_the_others(scratch_session: Session) -> None:
    legislation_id = _seed_legislation_id(scratch_session)
    CRUDLegislationAlias(scratch_session).add_many(_build_aliases(legislation_id))
    legislation_alias_id = scratch_session.exec(
        select(LegislationAlias.id).where(LegislationAlias.kind == AliasKind.SSO_CODE)
    ).one()
    assert legislation_alias_id is not None

    CRUDLegislationAlias(scratch_session).delete_by_ids([legislation_alias_id])

    legislation_alias_rows = CRUDLegislationAlias(scratch_session).get_rows()
    assert [
        legislation_alias_row.kind for legislation_alias_row in legislation_alias_rows
    ] == [AliasKind.FULL_TITLE, AliasKind.TITLE_WITHOUT_YEAR]
    assert CRUDLegislationAlias(scratch_session).get_count() == len(
        legislation_alias_rows
    )


def test_a_kind_outside_the_enum_is_refused(scratch_session: Session) -> None:
    legislation_id = _seed_legislation_id(scratch_session)
    legislation_alias = LegislationAlias(
        alias="Interpretation Act 1965",
        kind=AliasKind.FULL_TITLE,
        legislation_id=legislation_id,
    )
    legislation_alias.kind = "SHORT_TITLE"  # pyright: ignore[reportAttributeAccessIssue] the test stores a value outside the enum to reach the check constraint

    with pytest.raises(IntegrityError):
        CRUDLegislationAlias(scratch_session).add_many([legislation_alias])
