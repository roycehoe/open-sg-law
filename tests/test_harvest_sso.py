from collections.abc import Callable
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

import scripts.harvest_sso as harvest_sso_script
from crud.harvest_run import CRUDHarvestRun
from database.harvest_run import HarvestRun
from enums import HarvestRunStatus, SourceName
from exceptions import OpenSgLawWriteTargetError
from scripts.harvest_sso import harvest_sso
from tests.source_seed import seed_sources

_PROTECTED_DATABASE_URL = "postgresql://u:p@localhost:5435/x"
_HALT_REASON = "3 failures in a row"
_STARTED_AT = datetime(2026, 11, 5, 19, 0, tzinfo=timezone.utc)


class _LogRecorder:
    def __init__(self):
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


class _CallRecorder:
    def __init__(self):
        self.call_count = 0

    def __call__(self, *args: object) -> None:
        self.call_count += 1


class _FakeStage:
    def __init__(self, scratch_engine: Engine):
        self.scratch_engine = scratch_engine
        self.call_count = 0

    def __call__(self, session: Session, clock: Callable[[], datetime]) -> HarvestRun:
        self.call_count += 1
        with Session(self.scratch_engine) as stage_session:
            harvest_run = HarvestRun(
                source=SourceName.SSO,
                status=HarvestRunStatus.HALTED,
                halt_reason=_HALT_REASON,
                started_at=_STARTED_AT,
            )
            CRUDHarvestRun(stage_session).create(harvest_run)
            harvest_run_id = harvest_run.id
        stored_run = session.get(HarvestRun, harvest_run_id)
        assert stored_run is not None
        return stored_run


@pytest.fixture
def log_recorder(
    scratch_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> _LogRecorder:
    recorder = _LogRecorder()
    monkeypatch.setattr(harvest_sso_script, "engine", scratch_engine)
    monkeypatch.setattr(harvest_sso_script, "logger", recorder)
    return recorder


@pytest.fixture
def fake_stage(scratch_engine: Engine, monkeypatch: pytest.MonkeyPatch) -> _FakeStage:
    stage = _FakeStage(scratch_engine)
    monkeypatch.setattr(harvest_sso_script, "populate_sso_responses", stage)
    return stage


@pytest.fixture
def migration_recorder(monkeypatch: pytest.MonkeyPatch) -> _CallRecorder:
    recorder = _CallRecorder()
    monkeypatch.setattr(harvest_sso_script, "create_db_and_tables", recorder)
    return recorder


def test_a_dry_run_calls_no_stage_and_logs_the_state(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    fake_stage: _FakeStage,
    migration_recorder: _CallRecorder,
) -> None:
    seed_sources(scratch_session)

    harvest_sso(is_commit=False)

    assert fake_stage.call_count == 0
    assert migration_recorder.call_count == 0
    assert "SSO is UNTESTED: None" in log_recorder.messages
    assert "0 SSO PDFs are stored" in log_recorder.messages
    assert log_recorder.messages[-1] == "Dry run: nothing written"


def test_commit_refuses_the_protected_port_before_the_stage(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    fake_stage: _FakeStage,
    migration_recorder: _CallRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_sources(scratch_session)
    monkeypatch.setattr(
        harvest_sso_script,
        "settings",
        SimpleNamespace(database_url=_PROTECTED_DATABASE_URL),
    )

    with pytest.raises(OpenSgLawWriteTargetError, match="not 5435"):
        harvest_sso(is_commit=True)

    assert fake_stage.call_count == 0
    assert migration_recorder.call_count == 0
    assert log_recorder.messages == []


def test_commit_logs_the_status_of_a_run_read_back_from_the_database(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    fake_stage: _FakeStage,
    migration_recorder: _CallRecorder,
) -> None:
    seed_sources(scratch_session)

    harvest_sso(is_commit=True)

    assert fake_stage.call_count == 1
    assert migration_recorder.call_count == 1
    summary_line = log_recorder.messages[-1]
    assert summary_line.startswith("SSO run 1 HALTED: 0 sent")
    assert summary_line.endswith(f"halt reason {_HALT_REASON}")
