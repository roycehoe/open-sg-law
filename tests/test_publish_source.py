from collections.abc import Iterator
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import ProgrammingError
from sqlmodel import Session, SQLModel

import scripts.publish_source as publish_source_script
from crud.source import CRUDSource
from crud.source_grant import CRUDSourceGrant
from database.source import Source
from enums import PublishStatus, SourceName
from exceptions import (
    OpenSgLawReasonError,
    OpenSgLawSourceStateError,
    OpenSgLawWriteTargetError,
)
from scripts.publish_source import publish_source
from services.source_grants import SITE_ROLE_NAME, TABLE_NAME_TO_SOURCES
from tests.site_role_seed import (
    create_site_role,
    get_test_schema,
    has_site_role_select,
    revoke_site_role_grants,
)
from tests.source_seed import seed_sources

_PROTECTED_DATABASE_URL = "postgresql://u:p@localhost:5435/x"
_PUBLISH_REASON = "Permission letter dated 3 November 2026"
_WITHDRAW_REASON = "AGC asked on 4 November 2026 that the text come down"
_MISSING_ROLE_NAME = "open_sg_law_site_missing"
_SSO_TABLE_NAMES = (
    "act_history_entry",
    "legislation",
    "legislation_alias",
    "legislation_section",
    "legislation_version",
)
_SSO_FREE_TABLE_NAMES = ("bill", "bill_report", "source")


class _LogRecorder:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


@pytest.fixture
def site_role_schema(scratch_engine: Engine) -> Iterator[str]:
    create_site_role(scratch_engine)
    schema = get_test_schema(scratch_engine)
    yield schema
    revoke_site_role_grants(scratch_engine, schema)


@pytest.fixture
def log_recorder(
    scratch_engine: Engine, site_role_schema: str, monkeypatch: pytest.MonkeyPatch
) -> _LogRecorder:
    recorder = _LogRecorder()
    monkeypatch.setattr(publish_source_script, "engine", scratch_engine)
    monkeypatch.setattr(publish_source_script, "logger", recorder)
    monkeypatch.setattr(publish_source_script, "_PUBLIC_SCHEMA", site_role_schema)
    return recorder


def _grant_site_role(engine: Engine, schema: str, table_names: list[str]) -> None:
    with Session(engine) as session:
        for table_name in table_names:
            CRUDSourceGrant(session).grant_select(schema, table_name, SITE_ROLE_NAME)
        session.commit()


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


def test_publishing_grants_exactly_the_tables_of_the_published_sources(
    scratch_engine: Engine,
    scratch_session: Session,
    site_role_schema: str,
    log_recorder: _LogRecorder,
) -> None:
    seed_sources(scratch_session)

    publish_source(
        SourceName.ELITIGATION, _PUBLISH_REASON, is_withdrawal=False, is_commit=True
    )

    for table in SQLModel.metadata.sorted_tables:
        assert has_site_role_select(scratch_engine, site_role_schema, table.name) == (
            table.name in TABLE_NAME_TO_SOURCES
        )
    assert not has_site_role_select(scratch_engine, site_role_schema, "source_response")
    assert not has_site_role_select(scratch_engine, site_role_schema, "harvest_run")


def test_withdrawing_sso_revokes_its_tables_in_the_same_commit(
    scratch_engine: Engine,
    scratch_session: Session,
    site_role_schema: str,
    log_recorder: _LogRecorder,
) -> None:
    seed_sources(scratch_session)
    _grant_site_role(scratch_engine, site_role_schema, sorted(TABLE_NAME_TO_SOURCES))

    publish_source(SourceName.SSO, _WITHDRAW_REASON, is_withdrawal=True, is_commit=True)

    assert (
        _get_stored_source(scratch_engine, SourceName.SSO).publish_status
        == PublishStatus.UNPUBLISHED
    )
    for table_name in _SSO_TABLE_NAMES:
        assert not has_site_role_select(scratch_engine, site_role_schema, table_name)
        assert (
            f"Revoked SELECT on {table_name} from {SITE_ROLE_NAME}"
            in log_recorder.messages
        )
    for table_name in _SSO_FREE_TABLE_NAMES:
        assert has_site_role_select(scratch_engine, site_role_schema, table_name)


def test_publishing_elitigation_changes_no_grant(
    scratch_engine: Engine,
    scratch_session: Session,
    site_role_schema: str,
    log_recorder: _LogRecorder,
) -> None:
    seed_sources(scratch_session)
    _grant_site_role(scratch_engine, site_role_schema, sorted(TABLE_NAME_TO_SOURCES))

    publish_source(
        SourceName.ELITIGATION, _PUBLISH_REASON, is_withdrawal=False, is_commit=True
    )

    assert not any(
        message.startswith("Granted") or message.startswith("Revoked")
        for message in log_recorder.messages
    )
    for table_name in TABLE_NAME_TO_SOURCES:
        assert has_site_role_select(scratch_engine, site_role_schema, table_name)


def test_dry_run_logs_the_grant_changes_and_makes_none(
    scratch_engine: Engine,
    scratch_session: Session,
    site_role_schema: str,
    log_recorder: _LogRecorder,
) -> None:
    seed_sources(scratch_session)
    _grant_site_role(scratch_engine, site_role_schema, sorted(TABLE_NAME_TO_SOURCES))

    publish_source(
        SourceName.SSO, _WITHDRAW_REASON, is_withdrawal=True, is_commit=False
    )

    for table_name in _SSO_TABLE_NAMES:
        assert (
            f"Would revoke SELECT on {table_name} from {SITE_ROLE_NAME}"
            in log_recorder.messages
        )
    for table_name in TABLE_NAME_TO_SOURCES:
        assert has_site_role_select(scratch_engine, site_role_schema, table_name)
    assert (
        _get_stored_source(scratch_engine, SourceName.SSO).publish_status
        == PublishStatus.PUBLISHED
    )
    assert log_recorder.messages[-1] == "Dry run: nothing written"


def test_a_failed_grant_leaves_the_status_unchanged(
    scratch_engine: Engine,
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed_sources(scratch_session)
    monkeypatch.setattr(publish_source_script, "SITE_ROLE_NAME", _MISSING_ROLE_NAME)

    with pytest.raises(ProgrammingError, match="does not exist"):
        publish_source(
            SourceName.ELITIGATION,
            _PUBLISH_REASON,
            is_withdrawal=False,
            is_commit=True,
        )

    stored_source = _get_stored_source(scratch_engine, SourceName.ELITIGATION)
    assert stored_source.publish_status == PublishStatus.UNPUBLISHED
    assert stored_source.publish_status_reason is None
