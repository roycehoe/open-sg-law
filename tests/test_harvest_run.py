from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

from crud.database_size import CRUDDatabaseSize
from crud.harvest_run import CRUDHarvestRun
from database.harvest_run import HarvestRun
from enums import HarvestRunStatus, SourceName
from exceptions import OpenSgLawHarvestHaltError, OpenSgLawHarvestRunError
from services.harvest_run import (
    get_stale_run_cutoff,
    validate_can_send_after_failures,
    validate_can_start_harvest_run,
    validate_can_store_at_database_size,
)
from tests.source_seed import seed_sources

_RECENT_RUN_AGE = timedelta(hours=1)
_STALE_RUN_AGE = timedelta(hours=13)
_DATABASE_HALT_BYTES = 10 * 1_024**3


def _add_harvest_run(
    session: Session, source: SourceName, status: HarvestRunStatus, started_at: datetime
) -> None:
    CRUDHarvestRun(session).create(
        HarvestRun(source=source, status=status, started_at=started_at)
    )


def _get_running_sso_count(session: Session, now: datetime) -> int:
    return CRUDHarvestRun(session).get_count_by_source_and_status_and_started_at_after(
        SourceName.SSO, HarvestRunStatus.RUNNING, get_stale_run_cutoff(now)
    )


def test_a_recent_running_run_is_counted_and_blocks_a_start(
    scratch_session: Session,
) -> None:
    seed_sources(scratch_session)
    now = datetime.now(timezone.utc)
    _add_harvest_run(
        scratch_session, SourceName.SSO, HarvestRunStatus.RUNNING, now - _RECENT_RUN_AGE
    )

    running_count = _get_running_sso_count(scratch_session, now)

    assert running_count == 1
    with pytest.raises(OpenSgLawHarvestRunError, match="still RUNNING"):
        validate_can_start_harvest_run(running_count, SourceName.SSO)


def test_a_running_run_older_than_twelve_hours_is_not_counted(
    scratch_session: Session,
) -> None:
    seed_sources(scratch_session)
    now = datetime.now(timezone.utc)
    _add_harvest_run(
        scratch_session, SourceName.SSO, HarvestRunStatus.RUNNING, now - _STALE_RUN_AGE
    )

    assert _get_running_sso_count(scratch_session, now) == 0


def test_a_running_archive_run_is_not_counted_for_sso(
    scratch_session: Session,
) -> None:
    seed_sources(scratch_session)
    now = datetime.now(timezone.utc)
    _add_harvest_run(
        scratch_session,
        SourceName.INTERNET_ARCHIVE,
        HarvestRunStatus.RUNNING,
        now - _RECENT_RUN_AGE,
    )

    assert _get_running_sso_count(scratch_session, now) == 0


def test_a_succeeded_sso_run_is_not_counted(scratch_session: Session) -> None:
    seed_sources(scratch_session)
    now = datetime.now(timezone.utc)
    _add_harvest_run(
        scratch_session,
        SourceName.SSO,
        HarvestRunStatus.SUCCEEDED,
        now - _RECENT_RUN_AGE,
    )

    assert _get_running_sso_count(scratch_session, now) == 0


def test_no_running_run_lets_a_start_go_ahead() -> None:
    assert validate_can_start_harvest_run(0, SourceName.SSO) is None


def test_two_failures_in_a_row_let_the_next_request_go() -> None:
    assert validate_can_send_after_failures(2) is None


def test_three_failures_in_a_row_halt_the_run() -> None:
    with pytest.raises(OpenSgLawHarvestHaltError, match="3 failures in a row"):
        validate_can_send_after_failures(3)


def test_a_database_of_exactly_ten_gigabytes_may_store_more() -> None:
    assert validate_can_store_at_database_size(_DATABASE_HALT_BYTES) is None


def test_a_database_one_byte_past_ten_gigabytes_halts_the_run() -> None:
    with pytest.raises(OpenSgLawHarvestHaltError, match="past the 10 GB halt"):
        validate_can_store_at_database_size(_DATABASE_HALT_BYTES + 1)


def test_the_scratch_database_size_is_a_positive_number_of_bytes(
    scratch_session: Session,
) -> None:
    database_bytes = CRUDDatabaseSize(scratch_session).get_current_database_bytes()

    assert isinstance(database_bytes, int)
    assert database_bytes > 0


def test_a_stored_status_reads_back_equal_to_its_member_and_formats_as_its_name(
    scratch_engine: Engine, scratch_session: Session
) -> None:
    seed_sources(scratch_session)
    harvest_run = HarvestRun(
        source=SourceName.SSO,
        status=HarvestRunStatus.HALTED,
        started_at=datetime.now(timezone.utc),
    )
    CRUDHarvestRun(scratch_session).create(harvest_run)

    with Session(scratch_engine) as session:
        stored_run = session.get(HarvestRun, harvest_run.id)

        assert stored_run is not None
        assert stored_run.status == HarvestRunStatus.HALTED
        assert f"{stored_run.status}" == "HALTED"
