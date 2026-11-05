import argparse
from collections import Counter
from dataclasses import dataclass

from sqlmodel import Session

from crud.legislation_section import CRUDLegislationSection
from crud.legislation_version import CRUDLegislationVersion, VersionDocumentRow
from database.init import engine
from database.legislation_section import LegislationSection
from database.legislation_version import LegislationVersion
from enums import LegislationSectionKind
from exceptions import (
    OpenSgLawError,
    OpenSgLawPdfTextError,
    OpenSgLawSectionParseError,
    OpenSgLawWriteCheckError,
)
from logs import logger
from populate.legislation_sections import (
    VersionSections,
    get_version_sections,
    write_version_sections,
)
from populate.written_tables import vacuum_analyze_written_tables
from services.legislation_section import ParsedLegislation
from settings import settings
from utils.write_target import validate_can_write


@dataclass(frozen=True)
class _UnparsedVersion:
    legislation_version_id: int
    sso_code: str
    reason: str


class _SectionFigures:
    def __init__(self):
        self.kind_to_section_count: Counter[LegislationSectionKind] = Counter()
        self.repealed_section_count: int = 0
        self.image_page_section_count: int = 0
        self.body_character_count: int = 0
        self.section_character_count: int = 0

    def add(self, parsed_legislation: ParsedLegislation) -> None:
        for parsed_section in parsed_legislation.sections:
            self.kind_to_section_count[parsed_section.kind] += 1
            self.repealed_section_count += parsed_section.is_repealed
            self.image_page_section_count += parsed_section.is_on_image_page
        self.body_character_count += parsed_legislation.body_character_count
        self.section_character_count += parsed_legislation.section_character_count


def _build_unparsed_version(
    version_document_row: VersionDocumentRow, error: OpenSgLawError
) -> _UnparsedVersion:
    return _UnparsedVersion(
        legislation_version_id=version_document_row.id,
        sso_code=version_document_row.sso_code,
        reason=str(error),
    )


def _validate_can_commit_legislation_sections(
    session: Session, version_sections: VersionSections
) -> None:
    stored_count = CRUDLegislationSection(session).get_count_by_legislation_version_id(
        version_sections.legislation_version_id
    )
    planned_count = len(version_sections.parsed_legislation.sections)
    if stored_count != planned_count:
        raise OpenSgLawWriteCheckError(
            f"{stored_count} sections are stored for version {version_sections.legislation_version_id}, the parse has {planned_count}"
        )


def _log_figures(
    version_count: int,
    parsed_version_count: int,
    changed_version_count: int,
    section_figures: _SectionFigures,
    unparsed_versions: list[_UnparsedVersion],
) -> None:
    logger.info(f"{version_count:,} versions read")
    logger.info(f"{parsed_version_count:,} versions parsed")
    logger.info(f"{changed_version_count:,} versions changed")
    logger.info(f"{parsed_version_count - changed_version_count:,} versions unchanged")
    for section_kind, section_count in sorted(
        section_figures.kind_to_section_count.items()
    ):
        logger.info(f"{section_count:,} sections of kind {section_kind}")
    logger.info(f"{section_figures.repealed_section_count:,} repealed sections")
    logger.info(f"{section_figures.image_page_section_count:,} sections on image pages")
    if section_figures.body_character_count > 0:
        logger.info(
            f"Text share: {section_figures.section_character_count / section_figures.body_character_count:.2%}"
            " of the body characters land in a section"
        )
    for unparsed_version in unparsed_versions:
        logger.info(
            f"Unparsed {unparsed_version.sso_code} (version {unparsed_version.legislation_version_id}): {unparsed_version.reason}"
        )
    logger.info(f"{len(unparsed_versions):,} versions unparsed")


def apply_legislation_sections(is_commit: bool) -> None:
    if is_commit:
        validate_can_write(settings.database_url)
    section_figures = _SectionFigures()
    unparsed_versions: list[_UnparsedVersion] = []
    parsed_version_count = 0
    changed_version_count = 0
    with Session(engine) as session:
        version_document_rows = CRUDLegislationVersion(
            session
        ).get_version_document_rows()
        for version_document_row in version_document_rows:
            try:
                version_sections = get_version_sections(session, version_document_row)
            except OpenSgLawSectionParseError as error:
                unparsed_versions.append(
                    _build_unparsed_version(version_document_row, error)
                )
                continue
            except OpenSgLawPdfTextError as error:
                unparsed_versions.append(
                    _build_unparsed_version(version_document_row, error)
                )
                continue
            if is_commit:
                try:
                    write_version_sections(session, version_sections)
                    _validate_can_commit_legislation_sections(session, version_sections)
                except OpenSgLawWriteCheckError as error:
                    session.rollback()
                    unparsed_versions.append(
                        _build_unparsed_version(version_document_row, error)
                    )
                    continue
                session.commit()
            parsed_version_count += 1
            changed_version_count += version_sections.is_changed
            section_figures.add(version_sections.parsed_legislation)
        _log_figures(
            len(version_document_rows),
            parsed_version_count,
            changed_version_count,
            section_figures,
            unparsed_versions,
        )
        if not is_commit:
            logger.info("Dry run: nothing written")
            return
        logger.info("Committed")
        vacuum_analyze_written_tables(
            session,
            [
                LegislationSection.__tablename__,  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
                LegislationVersion.__tablename__,  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
            ],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build the sections of each stored version from its PDF, or with no --commit log what would change"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="write the legislation sections now",
    )
    arguments = parser.parse_args()
    apply_legislation_sections(arguments.commit)
