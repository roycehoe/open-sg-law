import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from crud.legislation_version import CRUDLegislationVersion, LegislationVersionRow
from database.legislation_version import LegislationVersion
from tests.document_seed import seed_version_inputs
from tests.legislation_version_seed import (
    CAPTURED_AT,
    VERSION_DATE,
    build_version,
)
from utils.legislation_version_update import LegislationVersionNewestUpdate

_BODY_CHARACTER_COUNT = 1_200
_SECTION_CHARACTER_COUNT = 1_100


def test_a_version_is_stored_with_its_counts_empty(scratch_session: Session) -> None:
    source_response_id = seed_version_inputs(scratch_session)

    CRUDLegislationVersion(scratch_session).add_many(
        [build_version(source_response_id)]
    )
    legislation_version_rows = CRUDLegislationVersion(scratch_session).get_rows()
    stored_version = scratch_session.exec(select(LegislationVersion)).one()

    assert CRUDLegislationVersion(scratch_session).get_count() == 1
    assert legislation_version_rows == [
        LegislationVersionRow(
            id=1,
            legislation_id=1,
            source_response_id=source_response_id,
            version_date=VERSION_DATE,
            captured_at=CAPTURED_AT,
            is_newest=False,
        )
    ]
    assert stored_version.body_character_count is None
    assert stored_version.section_character_count is None


def test_a_second_version_on_one_raw_row_is_refused(scratch_session: Session) -> None:
    source_response_id = seed_version_inputs(scratch_session)
    CRUDLegislationVersion(scratch_session).add_many(
        [build_version(source_response_id)]
    )

    with pytest.raises(IntegrityError):
        CRUDLegislationVersion(scratch_session).add_many(
            [build_version(source_response_id)]
        )


def test_the_newest_flag_changes_only_on_the_row_named(
    scratch_session: Session,
) -> None:
    source_response_id = seed_version_inputs(scratch_session)
    CRUDLegislationVersion(scratch_session).add_many(
        [build_version(source_response_id)]
    )

    updated_count = CRUDLegislationVersion(scratch_session).set_is_newest_bulk(
        [LegislationVersionNewestUpdate(id=1, is_newest=True)]
    )
    legislation_version_rows = CRUDLegislationVersion(scratch_session).get_rows()

    assert updated_count == 1
    assert legislation_version_rows[0].is_newest
    assert legislation_version_rows[0].version_date == VERSION_DATE


def test_an_empty_newest_update_writes_nothing(scratch_session: Session) -> None:
    updated_count = CRUDLegislationVersion(scratch_session).set_is_newest_bulk([])

    assert updated_count == 0


def test_both_character_counts_are_set_together(scratch_session: Session) -> None:
    source_response_id = seed_version_inputs(scratch_session)
    CRUDLegislationVersion(scratch_session).add_many(
        [build_version(source_response_id)]
    )

    CRUDLegislationVersion(scratch_session).update_character_counts(
        1, _BODY_CHARACTER_COUNT, _SECTION_CHARACTER_COUNT
    )
    scratch_session.expire_all()
    stored_version = scratch_session.exec(select(LegislationVersion)).one()

    assert stored_version.body_character_count == _BODY_CHARACTER_COUNT
    assert stored_version.section_character_count == _SECTION_CHARACTER_COUNT
