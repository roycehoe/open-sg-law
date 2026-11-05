from datetime import date, datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from crud.harvest_run import CRUDHarvestRun
from crud.legislation import CRUDLegislation
from crud.legislation_version import CRUDLegislationVersion, LegislationVersionRow
from crud.source_response import CRUDSourceResponse
from database.harvest_run import HarvestRun
from database.legislation import Legislation
from database.legislation_version import LegislationVersion
from database.source_response import SourceResponse
from enums import ResponseKind, SourceName
from tests.source_seed import seed_sources
from utils.legislation_version_update import LegislationVersionNewestUpdate

_CAPTURED_AT = datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)
_VERSION_DATE = date(2024, 11, 25)
_BODY_CHARACTER_COUNT = 1_200
_SECTION_CHARACTER_COUNT = 1_100


def _seed_version_inputs(session: Session) -> int:
    seed_sources(session)
    harvest_run = HarvestRun(source=SourceName.SSO)
    CRUDHarvestRun(session).create(harvest_run)
    assert harvest_run.id is not None
    CRUDSourceResponse(session).insert_on_conflict_do_nothing(
        SourceResponse(
            requested_url="https://sso.agc.gov.sg/Act/IA1965",
            final_url="https://sso.agc.gov.sg/Act/IA1965",
            status_code=200,
            body_bytes=b"%PDF-",
            sha256="a" * 64,
            byte_length=5,
            kind=ResponseKind.DOCUMENT,
            source=SourceName.SSO,
            harvest_run_id=harvest_run.id,
        )
    )
    CRUDLegislation(session).add_many(
        [
            Legislation(
                sso_code="IA1965",
                title="Interpretation Act 1965",
                is_in_newest_listing=True,
                listing_source=SourceName.SSO,
            )
        ]
    )
    session.commit()
    source_response_id = session.exec(select(SourceResponse.id)).one()
    assert source_response_id is not None
    return source_response_id


def _build_version(source_response_id: int) -> LegislationVersion:
    return LegislationVersion(
        printed_version_date="25/11/2024",
        version_date=_VERSION_DATE,
        captured_at=_CAPTURED_AT,
        is_newest=False,
        source=SourceName.SSO,
        legislation_id=1,
        source_response_id=source_response_id,
    )


def test_a_version_is_stored_with_its_counts_empty(scratch_session: Session) -> None:
    source_response_id = _seed_version_inputs(scratch_session)

    CRUDLegislationVersion(scratch_session).add_many(
        [_build_version(source_response_id)]
    )
    legislation_version_rows = CRUDLegislationVersion(scratch_session).get_rows()
    stored_version = scratch_session.exec(select(LegislationVersion)).one()

    assert CRUDLegislationVersion(scratch_session).get_count() == 1
    assert legislation_version_rows == [
        LegislationVersionRow(
            id=1,
            legislation_id=1,
            source_response_id=source_response_id,
            version_date=_VERSION_DATE,
            captured_at=_CAPTURED_AT,
            is_newest=False,
        )
    ]
    assert stored_version.body_character_count is None
    assert stored_version.section_character_count is None


def test_a_second_version_on_one_raw_row_is_refused(scratch_session: Session) -> None:
    source_response_id = _seed_version_inputs(scratch_session)
    CRUDLegislationVersion(scratch_session).add_many(
        [_build_version(source_response_id)]
    )

    with pytest.raises(IntegrityError):
        CRUDLegislationVersion(scratch_session).add_many(
            [_build_version(source_response_id)]
        )


def test_the_newest_flag_changes_only_on_the_row_named(
    scratch_session: Session,
) -> None:
    source_response_id = _seed_version_inputs(scratch_session)
    CRUDLegislationVersion(scratch_session).add_many(
        [_build_version(source_response_id)]
    )

    updated_count = CRUDLegislationVersion(scratch_session).set_is_newest_bulk(
        [LegislationVersionNewestUpdate(id=1, is_newest=True)]
    )
    legislation_version_rows = CRUDLegislationVersion(scratch_session).get_rows()

    assert updated_count == 1
    assert legislation_version_rows[0].is_newest
    assert legislation_version_rows[0].version_date == _VERSION_DATE


def test_an_empty_newest_update_writes_nothing(scratch_session: Session) -> None:
    updated_count = CRUDLegislationVersion(scratch_session).set_is_newest_bulk([])

    assert updated_count == 0


def test_both_character_counts_are_set_together(scratch_session: Session) -> None:
    source_response_id = _seed_version_inputs(scratch_session)
    CRUDLegislationVersion(scratch_session).add_many(
        [_build_version(source_response_id)]
    )

    CRUDLegislationVersion(scratch_session).update_character_counts(
        1, _BODY_CHARACTER_COUNT, _SECTION_CHARACTER_COUNT
    )
    scratch_session.expire_all()
    stored_version = scratch_session.exec(select(LegislationVersion)).one()

    assert stored_version.body_character_count == _BODY_CHARACTER_COUNT
    assert stored_version.section_character_count == _SECTION_CHARACTER_COUNT
