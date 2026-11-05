from datetime import datetime, timedelta, timezone

import pytest
from sqlmodel import Session

from crud.harvest_run import CRUDHarvestRun
from database.harvest_run import HarvestRun
from enums import HarvestRunStatus, SourceName
from exceptions import OpenSgLawHarvestRunError
from services.harvest_run import get_stale_run_cutoff, validate_can_start_harvest_run
from tests.source_seed import seed_sources

_RECENT_RUN_AGE = timedelta(hours=1)
_STALE_RUN_AGE = timedelta(hours=13)


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
