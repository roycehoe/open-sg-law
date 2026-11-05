from dataclasses import dataclass

from sqlmodel import Session

from crud.legislation_section import CRUDLegislationSection, LegislationSectionRow
from crud.legislation_version import CRUDLegislationVersion, VersionDocumentRow
from crud.source_response import CRUDSourceResponse
from database.legislation_section import LegislationSection
from services.legislation_section import ParsedLegislation, get_parsed_legislation
from utils.pdf_text import get_pdf_pages


@dataclass(frozen=True)
class UnparsedVersion:
    legislation_version_id: int
    sso_code: str
    reason: str


@dataclass(frozen=True)
class VersionSections:
    legislation_version_id: int
    parsed_legislation: ParsedLegislation
    is_changed: bool


def _build_section_rows(
    parsed_legislation: ParsedLegislation,
) -> list[LegislationSectionRow]:
    return [
        LegislationSectionRow(
            ordinal=parsed_section.ordinal,
            printed_number=parsed_section.printed_number,
            heading=parsed_section.heading,
            part_heading=parsed_section.part_heading,
            division_heading=parsed_section.division_heading,
            text=parsed_section.text,
            first_page_number=parsed_section.first_page_number,
            last_page_number=parsed_section.last_page_number,
            sso_anchor=parsed_section.sso_anchor,
            kind=parsed_section.kind,
            is_repealed=parsed_section.is_repealed,
            is_on_image_page=parsed_section.is_on_image_page,
        )
        for parsed_section in parsed_legislation.sections
    ]


def _build_legislation_sections(
    legislation_version_id: int, parsed_legislation: ParsedLegislation
) -> list[LegislationSection]:
    return [
        LegislationSection(
            ordinal=parsed_section.ordinal,
            printed_number=parsed_section.printed_number,
            heading=parsed_section.heading,
            part_heading=parsed_section.part_heading,
            division_heading=parsed_section.division_heading,
            text=parsed_section.text,
            first_page_number=parsed_section.first_page_number,
            last_page_number=parsed_section.last_page_number,
            sso_anchor=parsed_section.sso_anchor,
            kind=parsed_section.kind,
            is_repealed=parsed_section.is_repealed,
            is_on_image_page=parsed_section.is_on_image_page,
            legislation_version_id=legislation_version_id,
        )
        for parsed_section in parsed_legislation.sections
    ]


def get_version_sections(
    session: Session, version_document_row: VersionDocumentRow
) -> VersionSections:
    pdf_pages = get_pdf_pages(
        CRUDSourceResponse(session).get_body_bytes_by_id(
            version_document_row.source_response_id
        )
    )
    parsed_legislation = get_parsed_legislation(
        version_document_row.sso_code, pdf_pages
    )
    stored_section_rows = CRUDLegislationSection(
        session
    ).get_rows_by_legislation_version_id(version_document_row.id)
    return VersionSections(
        legislation_version_id=version_document_row.id,
        parsed_legislation=parsed_legislation,
        is_changed=stored_section_rows != _build_section_rows(parsed_legislation),
    )


def write_version_sections(session: Session, version_sections: VersionSections) -> None:
    if version_sections.is_changed:
        CRUDLegislationSection(session).delete_by_legislation_version_id(
            version_sections.legislation_version_id
        )
        CRUDLegislationSection(session).add_many(
            _build_legislation_sections(
                version_sections.legislation_version_id,
                version_sections.parsed_legislation,
            )
        )
    CRUDLegislationVersion(session).update_character_counts(
        version_sections.legislation_version_id,
        version_sections.parsed_legislation.body_character_count,
        version_sections.parsed_legislation.section_character_count,
    )
