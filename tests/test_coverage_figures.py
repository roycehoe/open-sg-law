from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

import scripts.coverage_figures as coverage_figures_script
from crud.act_history_entry import CRUDActHistoryEntry
from crud.bill import CRUDBill
from crud.legislation_section import CRUDLegislationSection
from crud.legislation_version import CRUDLegislationVersion
from database.act_history_entry import ActHistoryEntry
from database.bill import Bill
from database.legislation_section import LegislationSection
from enums import ActHistoryEntryKind, BillLinkSource, LegislationSectionKind
from exceptions import OpenSgLawWriteCheckError
from populate.coverage_figures import get_coverage_figures
from scripts.coverage_figures import coverage_figures
from services.coverage_figures import VersionTextShare
from tests.document_seed import seed_ia1965_version, seed_legislation
from tests.source_seed import seed_sources
from utils.legislation_version_update import LegislationVersionNewestUpdate

_LEGISLATION_COUNT = 2
_TEXT_SHARE = 0.95
_BODY_CHARACTER_COUNT = 200
_SECTION_CHARACTER_COUNT = 190
_EXPECTED_LINES = [
    "Acts listed: 2",
    "Acts with a version from SSO: 1",
    "Acts with no version: 1",
    "Newest versions printed in 2024: 1",
    "Newest versions with no printed date: 0",
    "Versions parsed: 1",
    "Versions not parsed: 0",
    "Sections of kind SCHEDULE: 1",
    "Sections of kind SECTION: 1",
    "Repealed sections: 1",
    "Sections on image pages: 1",
    "Text share, all parsed versions: 95.00%",
    "Versions under 99% text share: 1",
    "Versions under 90% text share: 0",
    "Lowest text share: IA1965 95.00%",
    "Bills: 1",
    "History entries: 2",
    "History entries linked to a bill: 1",
    "Judgment and subsidiary legislation figures wait for their parked steps",
]


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
    monkeypatch.setattr(coverage_figures_script, "engine", scratch_engine)
    monkeypatch.setattr(coverage_figures_script, "logger", recorder)
    return recorder


def _seed_figures(session: Session) -> None:
    legislation_version_id = seed_ia1965_version(session)
    seed_legislation(session, {"AA1906": "Appraisers Act 1906"})
    CRUDLegislationVersion(session).set_is_newest_bulk(
        [LegislationVersionNewestUpdate(id=legislation_version_id, is_newest=True)]
    )
    CRUDLegislationVersion(session).update_character_counts(
        legislation_version_id, _BODY_CHARACTER_COUNT, _SECTION_CHARACTER_COUNT
    )
    CRUDLegislationSection(session).add_many(
        [
            LegislationSection(
                ordinal=1,
                printed_number="2",
                text="2. Interpretation",
                first_page_number=1,
                last_page_number=1,
                sso_anchor="#pr2-",
                kind=LegislationSectionKind.SECTION,
                is_repealed=False,
                is_on_image_page=False,
                legislation_version_id=legislation_version_id,
            ),
            LegislationSection(
                ordinal=2,
                printed_number="THE SCHEDULE",
                text="THE SCHEDULE",
                first_page_number=2,
                last_page_number=2,
                kind=LegislationSectionKind.SCHEDULE,
                is_repealed=True,
                is_on_image_page=True,
                legislation_version_id=legislation_version_id,
            ),
        ]
    )
    bill = Bill(
        title="Competition Bill",
        title_key="competition",
        first_sitting_date=datetime(2004, 9, 1),
        last_sitting_date=datetime(2004, 10, 19),
        is_passed=True,
    )
    CRUDBill(session).add_many([bill])
    assert bill.id is not None
    CRUDActHistoryEntry(session).add_many(
        [
            ActHistoryEntry(
                ordinal=1,
                printed_text="Act 46 of 2004",
                printed_law_number="46",
                printed_title="Competition Act",
                kind=ActHistoryEntryKind.ACT,
                bill_link_source=BillLinkSource.FIRST_READING_DATE,
                legislation_id=1,
                bill_id=bill.id,
            ),
            ActHistoryEntry(
                ordinal=2,
                printed_text="Revised Edition 2006",
                printed_law_number="",
                printed_title="Competition Act",
                kind=ActHistoryEntryKind.REVISED_EDITION,
                legislation_id=1,
            ),
        ]
    )
    session.commit()


def test_the_figures_hold_the_seeded_counts(scratch_session: Session) -> None:
    _seed_figures(scratch_session)

    figures = get_coverage_figures(scratch_session)

    assert figures.legislation_count == _LEGISLATION_COUNT
    assert figures.legislation_without_version_count == 1
    assert figures.parsed_version_count == 1
    assert figures.unparsed_version_count == 0
    assert figures.overall_text_share == _TEXT_SHARE
    assert figures.lowest_text_shares == [VersionTextShare("IA1965", _TEXT_SHARE)]
    assert figures.repealed_section_count == 1
    assert figures.image_page_section_count == 1
    assert figures.bill_count == 1
    assert figures.linked_history_entry_count == 1


def test_the_lines_hold_the_seeded_counts(
    scratch_session: Session, log_recorder: _LogRecorder
) -> None:
    _seed_figures(scratch_session)

    coverage_figures(output=None)

    assert log_recorder.messages == _EXPECTED_LINES


def test_output_writes_the_same_lines(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    _seed_figures(scratch_session)
    output = tmp_path / "2026-11-05-first-write.txt"

    coverage_figures(output=output)

    assert output.read_text().splitlines() == log_recorder.messages


def test_an_existing_output_path_raises_and_keeps_its_text(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    _seed_figures(scratch_session)
    output = tmp_path / "2026-11-05-first-write.txt"
    output.write_text("kept")

    with pytest.raises(OpenSgLawWriteCheckError, match="exists"):
        coverage_figures(output=output)

    assert output.read_text() == "kept"


def test_a_database_with_no_versions_gives_no_text_share(
    scratch_session: Session,
) -> None:
    seed_sources(scratch_session)
    seed_legislation(scratch_session, {"IA1965": "Interpretation Act 1965"})

    figures = get_coverage_figures(scratch_session)

    assert figures.overall_text_share is None
    assert figures.lowest_text_shares == []
    assert figures.legislation_without_version_count == 1
