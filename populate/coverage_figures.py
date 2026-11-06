from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session

from crud.act_history_entry import CRUDActHistoryEntry
from crud.bill import CRUDBill
from crud.legislation import CRUDLegislation
from crud.legislation_section import CRUDLegislationSection, SectionKindCountRow
from crud.legislation_version import (
    CRUDLegislationVersion,
    SourceCountRow,
    VersionYearCountRow,
)
from crud.source_grant import CRUDSourceGrant
from services.coverage_figures import VersionTextShare, build_text_share_figures
from services.source_grants import SITE_ROLE_NAME

_SELECT_PRIVILEGE = "SELECT"
_SECTION_TABLE_NAMES = ("legislation", "legislation_version", "legislation_section")


@dataclass(frozen=True)
class CoverageFigures:
    current_legislation_count: int
    parsed_current_legislation_count: int
    is_section_text_readable: bool
    readable_current_legislation_count: int
    readable_current_legislation_share: Optional[float]
    legislation_count: int
    legislation_without_version_count: int
    source_counts: list[SourceCountRow]
    newest_version_year_counts: list[VersionYearCountRow]
    newest_version_without_date_count: int
    parsed_version_count: int
    unparsed_version_count: int
    section_kind_counts: list[SectionKindCountRow]
    repealed_section_count: int
    image_page_section_count: int
    overall_text_share: Optional[float]
    versions_under_high_share_count: int
    versions_under_low_share_count: int
    lowest_text_shares: list[VersionTextShare]
    bill_count: int
    history_entry_count: int
    linked_history_entry_count: int


def get_coverage_figures(session: Session) -> CoverageFigures:
    character_count_rows = CRUDLegislationVersion(
        session
    ).get_character_count_rows_by_body_character_count_not_null_and_section_character_count_not_null()
    newest_version_year_counts = CRUDLegislationVersion(
        session
    ).get_version_year_counts_by_is_newest(True)
    text_share_figures = build_text_share_figures(character_count_rows)
    current_legislation_count = CRUDLegislation(
        session
    ).get_count_by_is_in_newest_listing(True)
    parsed_current_legislation_count = CRUDLegislationVersion(
        session
    ).get_count_by_is_newest_and_section_character_count_not_null_and_legislation_is_in_newest_listing(
        True, True
    )
    is_section_text_readable = all(
        CRUDSourceGrant(
            session
        ).has_privilege_by_grantee_and_table_name_and_privilege_type(
            SITE_ROLE_NAME, table_name, _SELECT_PRIVILEGE
        )
        for table_name in _SECTION_TABLE_NAMES
    )
    readable_current_legislation_count = (
        parsed_current_legislation_count if is_section_text_readable else 0
    )
    return CoverageFigures(
        current_legislation_count=current_legislation_count,
        parsed_current_legislation_count=parsed_current_legislation_count,
        is_section_text_readable=is_section_text_readable,
        readable_current_legislation_count=readable_current_legislation_count,
        readable_current_legislation_share=(
            None
            if current_legislation_count == 0
            else readable_current_legislation_count / current_legislation_count
        ),
        legislation_count=CRUDLegislation(session).get_count(),
        legislation_without_version_count=CRUDLegislation(
            session
        ).get_count_by_legislation_version_none(),
        source_counts=CRUDLegislationVersion(
            session
        ).get_legislation_counts_by_source(),
        newest_version_year_counts=[
            version_year_count
            for version_year_count in newest_version_year_counts
            if version_year_count.version_year is not None
        ],
        newest_version_without_date_count=sum(
            version_year_count.version_count
            for version_year_count in newest_version_year_counts
            if version_year_count.version_year is None
        ),
        parsed_version_count=len(character_count_rows),
        unparsed_version_count=CRUDLegislationVersion(
            session
        ).get_count_by_body_character_count_null(),
        section_kind_counts=CRUDLegislationSection(session).get_counts_by_kind(),
        repealed_section_count=CRUDLegislationSection(session).get_count_by_is_repealed(
            True
        ),
        image_page_section_count=CRUDLegislationSection(
            session
        ).get_count_by_is_on_image_page(True),
        overall_text_share=text_share_figures.overall_text_share,
        versions_under_high_share_count=text_share_figures.versions_under_high_share_count,
        versions_under_low_share_count=text_share_figures.versions_under_low_share_count,
        lowest_text_shares=text_share_figures.lowest_text_shares,
        bill_count=CRUDBill(session).get_count(),
        history_entry_count=CRUDActHistoryEntry(session).get_count(),
        linked_history_entry_count=CRUDActHistoryEntry(
            session
        ).get_count_by_bill_id_not_null(),
    )
