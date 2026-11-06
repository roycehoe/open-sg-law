from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

import scripts.coverage_figures as coverage_figures_script
from crud.legislation_section import CRUDLegislationSection
from crud.legislation_version import CRUDLegislationVersion
from crud.source_grant import CRUDSourceGrant
from database.legislation_section import LegislationSection
from enums import LegislationSectionKind
from exceptions import OpenSgLawWriteCheckError
from populate.coverage_figures import get_coverage_figures
from scripts.coverage_figures import coverage_figures
from services.coverage_figures import VersionTextShare
from services.source_grants import SITE_ROLE_NAME
from tests.document_seed import seed_ia1965_version, seed_legislation
from tests.hansard_link_seed import add_competition_bill_and_history
from tests.source_seed import seed_sources
from utils.legislation_version_update import LegislationVersionNewestUpdate

_LEGISLATION_COUNT = 2
_TEXT_SHARE = 0.95
_BODY_CHARACTER_COUNT = 200
_SECTION_CHARACTER_COUNT = 190
_HEADLINE_SHARE = 0.5
_EXPECTED_LINES = [
    "Headline, current Acts the site can read section by section: 0 of 2 (0.00%)",
    "Current Acts with a parsed newest version: 1",
    "Site role reads legislation, versions and sections: no",
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
    scratch_engine: Engine, site_role_schema: str, monkeypatch: pytest.MonkeyPatch
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
    add_competition_bill_and_history(session, 1)
    session.commit()


def test_the_figures_hold_the_seeded_counts(
    scratch_session: Session, site_role_schema: str
) -> None:
    _seed_figures(scratch_session)

    figures = get_coverage_figures(scratch_session)

    assert figures.current_legislation_count == _LEGISLATION_COUNT
    assert figures.parsed_current_legislation_count == 1
    assert not figures.is_section_text_readable
    assert figures.readable_current_legislation_count == 0
    assert figures.readable_current_legislation_share == 0

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


def test_the_headline_counts_parsed_acts_once_the_site_role_reads_the_section_tables(
    scratch_session: Session, site_role_schema: str
) -> None:
    _seed_figures(scratch_session)
    for table_name in ("legislation", "legislation_version", "legislation_section"):
        CRUDSourceGrant(scratch_session).grant_select(
            site_role_schema, table_name, SITE_ROLE_NAME
        )
    scratch_session.commit()

    figures = get_coverage_figures(scratch_session)

    assert figures.is_section_text_readable
    assert figures.readable_current_legislation_count == 1
    assert figures.readable_current_legislation_share == _HEADLINE_SHARE


def test_the_headline_counts_nothing_while_one_section_table_is_not_granted(
    scratch_session: Session, site_role_schema: str
) -> None:
    _seed_figures(scratch_session)
    for table_name in ("legislation", "legislation_version"):
        CRUDSourceGrant(scratch_session).grant_select(
            site_role_schema, table_name, SITE_ROLE_NAME
        )
    scratch_session.commit()

    figures = get_coverage_figures(scratch_session)

    assert not figures.is_section_text_readable
    assert figures.readable_current_legislation_count == 0


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
    scratch_session: Session, site_role_schema: str
) -> None:
    seed_sources(scratch_session)
    seed_legislation(scratch_session, {"IA1965": "Interpretation Act 1965"})

    figures = get_coverage_figures(scratch_session)

    assert figures.overall_text_share is None
    assert figures.lowest_text_shares == []
    assert figures.legislation_without_version_count == 1
    assert figures.parsed_current_legislation_count == 0
