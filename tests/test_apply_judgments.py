from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

import scripts.apply_judgments as apply_judgments_script
from crud.judgment import CRUDJudgment
from crud.source_response import CRUDSourceResponse
from database.judgment import Judgment, JudgmentBlock
from enums import ResponseKind, SourceName
from exceptions import OpenSgLawWriteTargetError
from scripts.apply_judgments import apply_judgments
from services.source_response import build_source_response
from tests.document_seed import seed_harvest_run
from tests.source_seed import build_source_http_answer, seed_sources

_PROTECTED_DATABASE_URL = "postgresql://u:p@localhost:5435/x"
_HTML_CONTENT_TYPE = "text/html; charset=utf-8"
_JUDGMENT_URL = "https://www.elitigation.sg/gd/s/2099_SGHC_1"
_EARLIER = datetime(2026, 11, 7, tzinfo=timezone.utc)
_LATER = datetime(2026, 11, 8, tzinfo=timezone.utc)
_JUDGMENT_HTML = b'<html><head><title>[2099] SGHC 1</title></head><body><div id="divJudgement"><div class="Judg-1">1 Alpha sued.</div></div></body></html>'
_REVISED_JUDGMENT_HTML = b'<html><head><title>[2099] SGHC 1</title></head><body><div id="divJudgement"><div class="Judg-1">1 Alpha sued Beta.</div></div></body></html>'
_NOTICE_HTML = (
    b"<html><head><title>:: eLitigation - Maintenance Notice ::</title></head></html>"
)


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
    monkeypatch.setattr(apply_judgments_script, "engine", scratch_engine)
    monkeypatch.setattr(apply_judgments_script, "logger", recorder)
    monkeypatch.setattr(
        apply_judgments_script,
        "vacuum_analyze_written_tables",
        lambda session, table_names: None,
    )
    return recorder


def _seed_body(session: Session, body: bytes, fetched_at: datetime) -> None:
    source_response = build_source_response(
        build_source_http_answer(200, _HTML_CONTENT_TYPE, body),
        ResponseKind.DOCUMENT,
        SourceName.ELITIGATION,
        seed_harvest_run(session, SourceName.ELITIGATION),
    )
    source_response.requested_url = _JUDGMENT_URL
    source_response.final_url = _JUDGMENT_URL
    source_response.fetched_at = fetched_at
    CRUDSourceResponse(session).insert_on_conflict_do_nothing(source_response)
    session.commit()


def _get_block_texts(session: Session) -> list[str]:
    session.expire_all()
    return list(
        session.exec(select(JudgmentBlock.text).order_by(col(JudgmentBlock.ordinal))).all()
    )


def test_a_dry_run_writes_nothing_and_logs_the_figures(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)
    _seed_body(scratch_session, _JUDGMENT_HTML, _EARLIER)

    apply_judgments(is_commit=False)

    assert CRUDJudgment(scratch_session).get_count() == 0
    assert "1 judgments parsed" in log_recorder.messages
    assert log_recorder.messages[-1] == "Dry run: nothing written"


def test_commit_refuses_the_protected_port(
    log_recorder: _LogRecorder, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        apply_judgments_script,
        "settings",
        SimpleNamespace(database_url=_PROTECTED_DATABASE_URL),
    )

    with pytest.raises(OpenSgLawWriteTargetError, match="not 5435"):
        apply_judgments(is_commit=True)

    assert log_recorder.messages == []


def test_commit_stores_the_judgment_and_a_second_run_changes_nothing(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)
    _seed_body(scratch_session, _JUDGMENT_HTML, _EARLIER)

    apply_judgments(is_commit=True)
    stored_id = scratch_session.exec(select(Judgment.id)).one()
    apply_judgments(is_commit=True)

    assert _get_block_texts(scratch_session) == ["1 Alpha sued."]
    assert scratch_session.exec(select(Judgment.id)).one() == stored_id
    assert "0 judgments changed" in log_recorder.messages


def test_an_older_maintenance_notice_of_a_parsed_url_is_skipped(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)
    _seed_body(scratch_session, _NOTICE_HTML, _EARLIER)
    _seed_body(scratch_session, _JUDGMENT_HTML, _LATER)

    apply_judgments(is_commit=True)

    assert CRUDJudgment(scratch_session).get_count() == 1
    assert "1 older bodies of a parsed URL skipped" in log_recorder.messages
    assert "0 stored pages unparsed" in log_recorder.messages


def test_a_newer_body_of_the_same_url_replaces_the_stored_judgment(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)
    _seed_body(scratch_session, _JUDGMENT_HTML, _EARLIER)
    apply_judgments(is_commit=True)
    _seed_body(scratch_session, _REVISED_JUDGMENT_HTML, _LATER)

    apply_judgments(is_commit=True)

    assert CRUDJudgment(scratch_session).get_count() == 1
    assert _get_block_texts(scratch_session) == ["1 Alpha sued Beta."]


def test_a_newest_maintenance_notice_is_listed_and_the_older_judgment_is_kept(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    seed_sources(scratch_session)
    _seed_body(scratch_session, _JUDGMENT_HTML, _EARLIER)
    _seed_body(scratch_session, _NOTICE_HTML, _LATER)

    apply_judgments(is_commit=True)

    assert _get_block_texts(scratch_session) == ["1 Alpha sued."]
    assert (
        f"Unparsed {_JUDGMENT_URL}: The page title is not a neutral citation"
        in log_recorder.messages
    )
