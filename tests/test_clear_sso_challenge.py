from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

import scripts.clear_sso_challenge as clear_sso_challenge_script
from crud.source import CRUDSource
from database.source import Source
from enums import SourceName, SsoAccessState
from exceptions import (
    OpenSgLawReasonError,
    OpenSgLawSourceRowError,
    OpenSgLawSourceStateError,
    OpenSgLawWriteTargetError,
)
from scripts.clear_sso_challenge import clear_sso_challenge
from tests.source_seed import seed_sources

_PROTECTED_DATABASE_URL = "postgresql://u:p@localhost:5435/x"
_CHALLENGE_REASON = "The listing page answered 403"
_CHALLENGED_AT = datetime(2026, 11, 2, 3, 15, tzinfo=timezone.utc)
_CLEAR_REASON = "AGC replied on 4 November 2026"


class _LogRecorder:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


class _SessionRecorder:
    def __init__(self) -> None:
        self.opened_count = 0

    def __call__(self, *args: object) -> None:
        self.opened_count += 1


@pytest.fixture
def log_recorder(
    scratch_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> _LogRecorder:
    recorder = _LogRecorder()
    monkeypatch.setattr(clear_sso_challenge_script, "engine", scratch_engine)
    monkeypatch.setattr(clear_sso_challenge_script, "logger", recorder)
    return recorder


def _seed_sso_access_state(session: Session, sso_access_state: SsoAccessState) -> None:
    seed_sources(session)
    source = CRUDSource(session).get_by_name_for_update(SourceName.SSO)
    assert source is not None
    source.sso_access_state = sso_access_state
    source.sso_access_state_reason = _CHALLENGE_REASON
    source.sso_access_state_changed_at = _CHALLENGED_AT
    CRUDSource(session).update(source)
    session.commit()


def _get_stored_sso_source(engine: Engine) -> Source:
    with Session(engine) as session:
        source = CRUDSource(session).get_by_name(SourceName.SSO)
        assert source is not None
        return source


def test_dry_run_on_a_challenged_source_writes_nothing(
    scratch_engine: Engine, scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    _seed_sso_access_state(scratch_session, SsoAccessState.CHALLENGED)

    clear_sso_challenge(_CLEAR_REASON, is_commit=False)

    stored_source = _get_stored_sso_source(scratch_engine)
    assert stored_source.sso_access_state == SsoAccessState.CHALLENGED
    assert stored_source.sso_access_state_reason == _CHALLENGE_REASON
    assert stored_source.sso_access_state_changed_at == _CHALLENGED_AT
    assert log_recorder.messages[-1] == "Dry run: nothing written"


def test_commit_sets_untested_with_the_reason_and_a_time(
    scratch_engine: Engine, scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    _seed_sso_access_state(scratch_session, SsoAccessState.CHALLENGED)
    cleared_after = datetime.now(timezone.utc)

    clear_sso_challenge(_CLEAR_REASON, is_commit=True)

    stored_source = _get_stored_sso_source(scratch_engine)
    assert stored_source.sso_access_state == SsoAccessState.UNTESTED
    assert stored_source.sso_access_state_reason == _CLEAR_REASON
    assert stored_source.sso_access_state_changed_at is not None
    assert stored_source.sso_access_state_changed_at >= cleared_after
    assert "Committed" in log_recorder.messages


@pytest.mark.parametrize(
    "sso_access_state", [SsoAccessState.UNTESTED, SsoAccessState.SERVING]
)
def test_a_source_that_is_not_challenged_is_refused(
    scratch_engine: Engine,
    scratch_session: Session,
    log_recorder: _LogRecorder,
    sso_access_state: SsoAccessState,
) -> None:
    _seed_sso_access_state(scratch_session, sso_access_state)

    with pytest.raises(OpenSgLawSourceStateError, match="no challenge to clear"):
        clear_sso_challenge(_CLEAR_REASON, is_commit=True)

    assert _get_stored_sso_source(scratch_engine).sso_access_state == sso_access_state


def test_a_blank_reason_is_refused_before_any_session_opens(
    log_recorder: _LogRecorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_recorder = _SessionRecorder()
    monkeypatch.setattr(clear_sso_challenge_script, "Session", session_recorder)

    with pytest.raises(OpenSgLawReasonError, match="needs a reason"):
        clear_sso_challenge("   ", is_commit=True)

    assert session_recorder.opened_count == 0


def test_a_missing_source_row_is_refused(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    with pytest.raises(OpenSgLawSourceRowError, match="SSO source row is missing"):
        clear_sso_challenge(_CLEAR_REASON, is_commit=False)


def test_commit_refuses_the_protected_port_before_any_change(
    scratch_engine: Engine,
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_sso_access_state(scratch_session, SsoAccessState.CHALLENGED)
    monkeypatch.setattr(
        clear_sso_challenge_script,
        "settings",
        SimpleNamespace(database_url=_PROTECTED_DATABASE_URL),
    )

    with pytest.raises(OpenSgLawWriteTargetError, match="not 5435"):
        clear_sso_challenge(_CLEAR_REASON, is_commit=True)

    stored_source = _get_stored_sso_source(scratch_engine)
    assert stored_source.sso_access_state == SsoAccessState.CHALLENGED
    assert stored_source.sso_access_state_reason == _CHALLENGE_REASON
    assert log_recorder.messages == []
