from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

import populate.legislation_sections as legislation_sections_populate
import scripts.apply_legislation_sections as apply_legislation_sections_script
from crud.legislation_section import CRUDLegislationSection
from exceptions import OpenSgLawSectionParseError, OpenSgLawWriteTargetError
from populate.legislation_sections import VersionSections
from scripts.apply_legislation_sections import apply_legislation_sections
from services.legislation_section import ParsedLegislation
from tests.document_seed import seed_ia1965_version
from utils.pdf_text import PdfPage

_PROTECTED_DATABASE_URL = "postgresql://u:p@localhost:5435/x"
_QUOTATION_OPEN_MESSAGE = "IA1965 leaves a quotation open"


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
    monkeypatch.setattr(apply_legislation_sections_script, "engine", scratch_engine)
    monkeypatch.setattr(apply_legislation_sections_script, "logger", recorder)
    return recorder


def test_a_dry_run_writes_nothing_and_logs_the_figures(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    legislation_version_id = seed_ia1965_version(scratch_session)

    apply_legislation_sections(is_commit=False)

    assert (
        CRUDLegislationSection(scratch_session).get_count_by_legislation_version_id(
            legislation_version_id
        )
        == 0
    )
    assert log_recorder.messages == [
        "1 versions read",
        "1 versions parsed",
        "1 versions changed",
        "0 versions unchanged",
        "1 sections of kind SECTION",
        "0 repealed sections",
        "0 sections on image pages",
        "Text share: 100.00% of the body characters land in a section",
        "0 versions unparsed",
        "Dry run: nothing written",
    ]


def test_commit_writes_the_sections_and_a_second_run_changes_nothing(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    legislation_version_id = seed_ia1965_version(scratch_session)

    apply_legislation_sections(is_commit=True)

    assert (
        CRUDLegislationSection(scratch_session).get_count_by_legislation_version_id(
            legislation_version_id
        )
        == 1
    )
    assert "1 versions changed" in log_recorder.messages
    assert "Committed" in log_recorder.messages
    log_recorder.messages.clear()

    apply_legislation_sections(is_commit=True)

    assert "0 versions changed" in log_recorder.messages
    assert "1 versions unchanged" in log_recorder.messages


def test_a_version_the_parser_cannot_parse_is_listed_and_gets_no_rows(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legislation_version_id = seed_ia1965_version(scratch_session)

    def raise_parse_error(sso_code: str, pdf_pages: list[PdfPage]) -> ParsedLegislation:
        raise OpenSgLawSectionParseError(_QUOTATION_OPEN_MESSAGE)

    monkeypatch.setattr(
        legislation_sections_populate, "get_parsed_legislation", raise_parse_error
    )

    apply_legislation_sections(is_commit=True)

    assert (
        CRUDLegislationSection(scratch_session).get_count_by_legislation_version_id(
            legislation_version_id
        )
        == 0
    )
    assert (
        f"Unparsed IA1965 (version {legislation_version_id}): {_QUOTATION_OPEN_MESSAGE}"
        in log_recorder.messages
    )
    assert "1 versions unparsed" in log_recorder.messages
    assert "1 versions parsed" not in log_recorder.messages


def test_a_version_whose_stored_count_misses_the_parse_is_rolled_back_and_listed(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legislation_version_id = seed_ia1965_version(scratch_session)

    def skip_write(session: Session, version_sections: VersionSections) -> None:
        return None

    monkeypatch.setattr(
        apply_legislation_sections_script, "write_version_sections", skip_write
    )

    apply_legislation_sections(is_commit=True)

    assert (
        CRUDLegislationSection(scratch_session).get_count_by_legislation_version_id(
            legislation_version_id
        )
        == 0
    )
    assert (
        f"Unparsed IA1965 (version {legislation_version_id}): "
        f"0 sections are stored for version {legislation_version_id}, the parse has 1"
        in log_recorder.messages
    )


def test_commit_refuses_the_protected_port_before_any_write(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legislation_version_id = seed_ia1965_version(scratch_session)
    monkeypatch.setattr(
        apply_legislation_sections_script,
        "settings",
        SimpleNamespace(database_url=_PROTECTED_DATABASE_URL),
    )

    with pytest.raises(OpenSgLawWriteTargetError, match="not 5435"):
        apply_legislation_sections(is_commit=True)

    assert (
        CRUDLegislationSection(scratch_session).get_count_by_legislation_version_id(
            legislation_version_id
        )
        == 0
    )
    assert log_recorder.messages == []
