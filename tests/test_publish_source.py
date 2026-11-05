from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

import scripts.publish_source as publish_source_script
from crud.source import CRUDSource
from database.source import Source
from enums import PublishStatus, SourceName
from exceptions import (
    OpenSgLawReasonError,
    OpenSgLawSourceStateError,
    OpenSgLawWriteTargetError,
)
from scripts.publish_source import publish_source
from tests.source_seed import seed_sources

_PROTECTED_DATABASE_URL = "postgresql://u:p@localhost:5435/x"
_PUBLISH_REASON = "Permission letter dated 3 November 2026"
_WITHDRAW_REASON = "AGC asked on 4 November 2026 that the text come down"


class _LogRecorder:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


@pytest.fixture
def log_recorder(
    scratch_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> _LogRecorder:
    recorder = _LogRecorder()
    monkeypatch.setattr(publish_source_script, "engine", scratch_engine)
    monkeypatch.setattr(publish_source_script, "logger", recorder)
    return recorder


def _get_stored_source(engine: Engine, source_name: SourceName) -> Source:
    with Session(engine) as session:
        source = CRUDSource(session).get_by_name(source_name)
        assert source is not None
        return source


def test_publishing_elitigation_sets_published_with_the_reason(
    scratch_engine: Engine, scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)
    published_after = datetime.now(timezone.utc)

    publish_source(
        SourceName.ELITIGATION, _PUBLISH_REASON, is_withdrawal=False, is_commit=True
    )

    stored_source = _get_stored_source(scratch_engine, SourceName.ELITIGATION)
    assert stored_source.publish_status == PublishStatus.PUBLISHED
    assert stored_source.publish_status_reason == _PUBLISH_REASON
    assert stored_source.publish_status_changed_at is not None
    assert stored_source.publish_status_changed_at >= published_after
    assert "Committed" in log_recorder.messages


def test_withdrawing_sso_sets_unpublished(
    scratch_engine: Engine, scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)

    publish_source(SourceName.SSO, _WITHDRAW_REASON, is_withdrawal=True, is_commit=True)

    stored_source = _get_stored_source(scratch_engine, SourceName.SSO)
    assert stored_source.publish_status == PublishStatus.UNPUBLISHED
    assert stored_source.publish_status_reason == _WITHDRAW_REASON


def test_publishing_a_published_source_is_refused(
    scratch_engine: Engine, scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)

    with pytest.raises(OpenSgLawSourceStateError, match="SSO is already PUBLISHED"):
        publish_source(
            SourceName.SSO, _PUBLISH_REASON, is_withdrawal=False, is_commit=True
        )

    stored_source = _get_stored_source(scratch_engine, SourceName.SSO)
    assert stored_source.publish_status_reason is None


def test_a_blank_reason_is_refused_as_a_reason_error(
    scratch_engine: Engine, scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)

    with pytest.raises(OpenSgLawReasonError, match="needs a reason"):
        publish_source(SourceName.SSO, " ", is_withdrawal=False, is_commit=True)

    assert (
        _get_stored_source(scratch_engine, SourceName.SSO).publish_status
        == PublishStatus.PUBLISHED
    )


def test_dry_run_writes_nothing(
    scratch_engine: Engine, scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)

    publish_source(
        SourceName.ELITIGATION, _PUBLISH_REASON, is_withdrawal=False, is_commit=False
    )

    stored_source = _get_stored_source(scratch_engine, SourceName.ELITIGATION)
    assert stored_source.publish_status == PublishStatus.UNPUBLISHED
    assert stored_source.publish_status_reason is None
    assert stored_source.publish_status_changed_at is None
    assert log_recorder.messages[-1] == "Dry run: nothing written"


def test_commit_refuses_the_protected_port_before_any_change(
    scratch_engine: Engine,
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_sources(scratch_session)
    monkeypatch.setattr(
        publish_source_script,
        "settings",
        SimpleNamespace(database_url=_PROTECTED_DATABASE_URL),
    )

    with pytest.raises(OpenSgLawWriteTargetError, match="not 5435"):
        publish_source(
            SourceName.ELITIGATION,
            _PUBLISH_REASON,
            is_withdrawal=False,
            is_commit=True,
        )

    stored_source = _get_stored_source(scratch_engine, SourceName.ELITIGATION)
    assert stored_source.publish_status == PublishStatus.UNPUBLISHED
    assert stored_source.publish_status_reason is None
    assert log_recorder.messages == []
