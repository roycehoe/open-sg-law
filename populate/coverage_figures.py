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

_HIGH_TEXT_SHARE = 0.99
_LOW_TEXT_SHARE = 0.9
_LOWEST_TEXT_SHARE_COUNT = 5


@dataclass(frozen=True)
class VersionTextShare:
    sso_code: str
    text_share: float


@dataclass(frozen=True)
class CoverageFigures:
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
    body_character_count = sum(
        character_count_row.body_character_count
        for character_count_row in character_count_rows
    )
    version_text_shares = sorted(
        (
            VersionTextShare(
                sso_code=character_count_row.sso_code,
                text_share=character_count_row.section_character_count
                / character_count_row.body_character_count,
            )
            for character_count_row in character_count_rows
        ),
        key=lambda version_text_share: (
            version_text_share.text_share,
            version_text_share.sso_code,
        ),
    )
    return CoverageFigures(
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
        overall_text_share=(
            None
            if body_character_count == 0
            else sum(
                character_count_row.section_character_count
                for character_count_row in character_count_rows
            )
            / body_character_count
        ),
        versions_under_high_share_count=sum(
            version_text_share.text_share < _HIGH_TEXT_SHARE
            for version_text_share in version_text_shares
        ),
        versions_under_low_share_count=sum(
            version_text_share.text_share < _LOW_TEXT_SHARE
            for version_text_share in version_text_shares
        ),
        lowest_text_shares=version_text_shares[:_LOWEST_TEXT_SHARE_COUNT],
        bill_count=CRUDBill(session).get_count(),
        history_entry_count=CRUDActHistoryEntry(session).get_count(),
        linked_history_entry_count=CRUDActHistoryEntry(
            session
        ).get_count_by_bill_id_not_null(),
    )
