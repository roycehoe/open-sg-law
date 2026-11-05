from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

import scripts.apply_legislation_aliases as apply_legislation_aliases_script
from crud.legislation_alias import CRUDLegislationAlias
from enums import SourceName
from exceptions import OpenSgLawWriteCheckError, OpenSgLawWriteTargetError
from populate.legislation import get_legislation_write, write_legislation
from scripts.apply_legislation_aliases import apply_legislation_aliases
from services.legislation_alias import LegislationAliasWrite
from tests.listing_seed import seed_listing
from tests.source_seed import seed_sources

_PROTECTED_DATABASE_URL = "postgresql://u:p@localhost:5435/x"
_ARCHIVE_FETCHED_AT = datetime(2026, 11, 5, 18, 0, tzinfo=timezone.utc)
_DATED_TITLE_ALIAS_COUNT = 18


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
    monkeypatch.setattr(apply_legislation_aliases_script, "engine", scratch_engine)
    monkeypatch.setattr(apply_legislation_aliases_script, "logger", recorder)
    return recorder


def _seed_legislation(session: Session) -> None:
    seed_sources(session)
    seed_listing(session, SourceName.INTERNET_ARCHIVE, _ARCHIVE_FETCHED_AT)
    write_legislation(session, get_legislation_write(session))
    session.commit()


def test_a_dry_run_writes_nothing_and_logs_the_counts(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    _seed_legislation(scratch_session)

    apply_legislation_aliases(is_commit=False)

    assert CRUDLegislationAlias(scratch_session).get_count() == 0
    assert log_recorder.messages == [
        "18 legislation aliases to insert",
        "0 legislation aliases to delete",
        "0 legislation aliases unchanged",
        "Dry run: nothing written",
    ]


def test_commit_writes_the_planned_aliases(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    _seed_legislation(scratch_session)

    apply_legislation_aliases(is_commit=True)

    assert CRUDLegislationAlias(scratch_session).get_count() == _DATED_TITLE_ALIAS_COUNT
    assert log_recorder.messages[0] == "18 legislation aliases to insert"
    assert "Committed" in log_recorder.messages


def test_commit_refuses_the_protected_port_before_any_write(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_legislation(scratch_session)
    monkeypatch.setattr(
        apply_legislation_aliases_script,
        "settings",
        SimpleNamespace(database_url=_PROTECTED_DATABASE_URL),
    )

    with pytest.raises(OpenSgLawWriteTargetError, match="not 5435"):
        apply_legislation_aliases(is_commit=True)

    assert CRUDLegislationAlias(scratch_session).get_count() == 0
    assert log_recorder.messages == []


def test_commit_stores_nothing_when_the_stored_count_misses_the_plan(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_legislation(scratch_session)

    def skip_write(
        session: Session, legislation_alias_write: LegislationAliasWrite
    ) -> None:
        return None

    monkeypatch.setattr(
        apply_legislation_aliases_script, "write_legislation_aliases", skip_write
    )

    with pytest.raises(
        OpenSgLawWriteCheckError,
        match="0 legislation aliases are stored, the plan has 18",
    ):
        apply_legislation_aliases(is_commit=True)

    assert CRUDLegislationAlias(scratch_session).get_count() == 0
    assert "Committed" not in log_recorder.messages
