from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

import scripts.apply_legislation_versions as apply_legislation_versions_script
from crud.legislation_version import CRUDLegislationVersion
from crud.vacuum import CRUDVacuum
from database.legislation_version import LegislationVersion
from enums import SourceName
from exceptions import OpenSgLawWriteCheckError, OpenSgLawWriteTargetError
from populate.legislation_versions import LegislationVersionWrite
from scripts.apply_legislation_versions import apply_legislation_versions
from tests.document_seed import (
    AA1906_ARCHIVE_URL,
    AA1906_BODY,
    ARCHIVE_FETCHED_AT,
    IA1965_ARCHIVE_URL,
    IA1965_BODY,
    IA1965_POINT_IN_TIME_URL,
    SSO_FETCHED_AT,
    seed_document,
    seed_harvest_run,
    seed_legislation,
)
from tests.source_seed import seed_sources

_PROTECTED_DATABASE_URL = "postgresql://u:p@localhost:5435/x"
_VERSION_COUNT = 2


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
    monkeypatch.setattr(apply_legislation_versions_script, "engine", scratch_engine)
    monkeypatch.setattr(apply_legislation_versions_script, "logger", recorder)
    return recorder


def _seed_documents(session: Session) -> None:
    seed_sources(session)
    seed_legislation(
        session,
        {"IA1965": "Interpretation Act 1965", "AA1906": "Appraisers Act 1906"},
    )
    archive_harvest_run_id = seed_harvest_run(session, SourceName.INTERNET_ARCHIVE)
    sso_harvest_run_id = seed_harvest_run(session, SourceName.SSO)
    seed_document(
        session,
        archive_harvest_run_id,
        SourceName.INTERNET_ARCHIVE,
        IA1965_ARCHIVE_URL,
        IA1965_BODY,
        ARCHIVE_FETCHED_AT,
    )
    seed_document(
        session,
        archive_harvest_run_id,
        SourceName.INTERNET_ARCHIVE,
        AA1906_ARCHIVE_URL,
        AA1906_BODY,
        ARCHIVE_FETCHED_AT,
    )
    seed_document(
        session,
        sso_harvest_run_id,
        SourceName.SSO,
        IA1965_POINT_IN_TIME_URL,
        IA1965_BODY,
        SSO_FETCHED_AT,
    )


def test_a_dry_run_writes_nothing_and_logs_the_counts(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    _seed_documents(scratch_session)

    apply_legislation_versions(is_commit=False)

    assert CRUDLegislationVersion(scratch_session).get_count() == 0
    assert log_recorder.messages == [
        "3 documents read",
        "2 versions to insert",
        "2 versions to insert from INTERNET_ARCHIVE",
        "1 versions to insert with printed date form footer",
        "1 versions to insert with printed date form in force",
        "1 documents skipped",
        f"Skipped {IA1965_POINT_IN_TIME_URL}: not a plain Act PDF",
        "0 CDX answers skipped",
        "Dry run: nothing written",
    ]


def test_commit_writes_the_versions_and_vacuums_the_table(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    _seed_documents(scratch_session)
    table_name: str = LegislationVersion.__tablename__  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr
    vacuum_count_before = CRUDVacuum(scratch_session).get_vacuum_count(table_name)

    apply_legislation_versions(is_commit=True)

    scratch_session.commit()
    assert CRUDLegislationVersion(scratch_session).get_count() == _VERSION_COUNT
    assert [
        legislation_version_row.is_newest
        for legislation_version_row in CRUDLegislationVersion(
            scratch_session
        ).get_rows()
    ] == [True, True]
    assert (
        CRUDVacuum(scratch_session).get_vacuum_count(table_name) > vacuum_count_before
    )
    assert "Committed" in log_recorder.messages
    assert "2 newest flags changed" in log_recorder.messages


def test_a_second_commit_changes_nothing(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    _seed_documents(scratch_session)
    apply_legislation_versions(is_commit=True)
    log_recorder.messages.clear()

    apply_legislation_versions(is_commit=True)

    assert CRUDLegislationVersion(scratch_session).get_count() == _VERSION_COUNT
    assert log_recorder.messages[:2] == ["3 documents read", "0 versions to insert"]
    assert "0 newest flags changed" in log_recorder.messages


def test_commit_refuses_the_protected_port_before_any_write(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_documents(scratch_session)
    monkeypatch.setattr(
        apply_legislation_versions_script,
        "settings",
        SimpleNamespace(database_url=_PROTECTED_DATABASE_URL),
    )

    with pytest.raises(OpenSgLawWriteTargetError, match="not 5435"):
        apply_legislation_versions(is_commit=True)

    assert CRUDLegislationVersion(scratch_session).get_count() == 0
    assert log_recorder.messages == []


def test_commit_stores_nothing_when_the_stored_count_misses_the_plan(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_documents(scratch_session)

    def skip_write(
        session: Session, legislation_version_write: LegislationVersionWrite
    ) -> int:
        return 0

    monkeypatch.setattr(
        apply_legislation_versions_script, "write_legislation_versions", skip_write
    )

    with pytest.raises(
        OpenSgLawWriteCheckError,
        match="0 legislation versions are stored, the plan has 2",
    ):
        apply_legislation_versions(is_commit=True)

    assert CRUDLegislationVersion(scratch_session).get_count() == 0
    assert "Committed" not in log_recorder.messages
