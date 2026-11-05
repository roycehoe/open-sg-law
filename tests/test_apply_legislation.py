from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

import scripts.apply_legislation as apply_legislation_script
from crud.legislation import CRUDLegislation
from enums import SourceName
from exceptions import OpenSgLawWriteCheckError, OpenSgLawWriteTargetError
from scripts.apply_legislation import apply_legislation
from services.legislation import LegislationWrite
from tests.listing_seed import seed_listing
from tests.source_seed import seed_sources

_PROTECTED_DATABASE_URL = "postgresql://u:p@localhost:5435/x"
_ARCHIVE_FETCHED_AT = datetime(2026, 11, 5, 18, 0, tzinfo=timezone.utc)
_SSO_FETCHED_AT = datetime(2026, 11, 5, 19, 0, tzinfo=timezone.utc)
_CODE_COUNT = 6


class _LogRecorder:
    def __init__(self):
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


@pytest.fixture
def log_recorder(
    scratch_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> _LogRecorder:
    recorder = _LogRecorder()
    monkeypatch.setattr(apply_legislation_script, "engine", scratch_engine)
    monkeypatch.setattr(apply_legislation_script, "logger", recorder)
    return recorder


def test_a_dry_run_writes_nothing_and_logs_the_counts(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)
    seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, _ARCHIVE_FETCHED_AT)
    seed_listing(scratch_session, SourceName.SSO, _SSO_FETCHED_AT, page_indexes=(0,))

    apply_legislation(is_commit=False)

    assert CRUDLegislation(scratch_session).get_count() == 0
    assert log_recorder.messages == [
        "6 legislation rows to insert",
        "0 legislation rows to update",
        "0 legislation rows unchanged",
        "Listing run 2 is incomplete and gives no rows",
        "Dry run: nothing written",
    ]


def test_commit_writes_the_planned_rows(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)
    seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, _ARCHIVE_FETCHED_AT)

    apply_legislation(is_commit=True)

    legislation_rows = CRUDLegislation(scratch_session).get_rows()
    assert len(legislation_rows) == _CODE_COUNT
    assert {legislation_row.listing_source for legislation_row in legislation_rows} == {
        SourceName.INTERNET_ARCHIVE
    }
    assert log_recorder.messages[0] == "6 legislation rows to insert"
    assert "Committed" in log_recorder.messages


def test_a_second_commit_changes_nothing(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)
    seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, _ARCHIVE_FETCHED_AT)
    apply_legislation(is_commit=True)
    log_recorder.messages.clear()

    apply_legislation(is_commit=True)

    assert CRUDLegislation(scratch_session).get_count() == _CODE_COUNT
    assert log_recorder.messages[:3] == [
        "0 legislation rows to insert",
        "0 legislation rows to update",
        "6 legislation rows unchanged",
    ]


def test_commit_refuses_the_protected_port_before_any_write(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_sources(scratch_session)
    seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, _ARCHIVE_FETCHED_AT)
    monkeypatch.setattr(
        apply_legislation_script,
        "settings",
        SimpleNamespace(database_url=_PROTECTED_DATABASE_URL),
    )

    with pytest.raises(OpenSgLawWriteTargetError, match="not 5435"):
        apply_legislation(is_commit=True)

    assert CRUDLegislation(scratch_session).get_count() == 0
    assert log_recorder.messages == []


def test_commit_stores_nothing_when_the_stored_count_misses_the_plan(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_sources(scratch_session)
    seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, _ARCHIVE_FETCHED_AT)

    def skip_write(session: Session, legislation_write: LegislationWrite) -> None:
        return None

    monkeypatch.setattr(apply_legislation_script, "write_legislation", skip_write)

    with pytest.raises(
        OpenSgLawWriteCheckError, match="0 legislation rows are stored, the plan has 6"
    ):
        apply_legislation(is_commit=True)

    assert CRUDLegislation(scratch_session).get_count() == 0
    assert "Committed" not in log_recorder.messages
