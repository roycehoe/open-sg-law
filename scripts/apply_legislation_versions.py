import argparse
from collections import Counter

from sqlmodel import Session

from crud.legislation_version import CRUDLegislationVersion
from database.init import engine
from database.legislation_version import LegislationVersion
from exceptions import OpenSgLawWriteCheckError
from logs import logger
from populate.legislation_versions import (
    LegislationVersionWrite,
    get_legislation_version_write,
    write_legislation_versions,
)
from populate.written_tables import vacuum_analyze_written_tables
from services.legislation_version import get_printed_date_form
from settings import settings
from utils.write_target import validate_can_write


def _log_write(legislation_version_write: LegislationVersionWrite) -> None:
    logger.info(f"{legislation_version_write.document_count:,} documents read")
    legislation_versions_to_insert = (
        legislation_version_write.legislation_versions_to_insert
    )
    logger.info(f"{len(legislation_versions_to_insert):,} versions to insert")
    for source, version_count in sorted(
        Counter(
            legislation_version.source
            for legislation_version in legislation_versions_to_insert
        ).items()
    ):
        logger.info(f"{version_count:,} versions to insert from {source}")
    for printed_date_form, version_count in sorted(
        Counter(
            get_printed_date_form(legislation_version.printed_version_date)
            for legislation_version in legislation_versions_to_insert
        ).items()
    ):
        logger.info(
            f"{version_count:,} versions to insert with printed date form {printed_date_form}"
        )
    logger.info(
        f"{len(legislation_version_write.skipped_documents):,} documents skipped"
    )
    for skipped_document in legislation_version_write.skipped_documents:
        logger.info(
            f"Skipped {skipped_document.requested_url}: {skipped_document.reason}"
        )
    logger.info(
        f"{legislation_version_write.skipped_cdx_answer_count:,} CDX answers skipped"
    )


def _validate_can_commit_legislation_versions(
    session: Session, planned_count: int
) -> None:
    stored_count = CRUDLegislationVersion(session).get_count()
    if stored_count != planned_count:
        raise OpenSgLawWriteCheckError(
            f"{stored_count} legislation versions are stored, the plan has {planned_count}"
        )


def apply_legislation_versions(is_commit: bool) -> None:
    if not is_commit:
        with Session(engine) as session:
            _log_write(get_legislation_version_write(session))
        logger.info("Dry run: nothing written")
        return
    validate_can_write(settings.database_url)
    with Session(engine) as session:
        legislation_version_write = get_legislation_version_write(session)
        _log_write(legislation_version_write)
        planned_count = CRUDLegislationVersion(session).get_count() + len(
            legislation_version_write.legislation_versions_to_insert
        )
        newest_flag_count = write_legislation_versions(
            session, legislation_version_write
        )
        _validate_can_commit_legislation_versions(session, planned_count)
        session.commit()
        logger.info("Committed")
        logger.info(f"{newest_flag_count:,} newest flags changed")
        vacuum_analyze_written_tables(
            session,
            [LegislationVersion.__tablename__],  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build a legislation version from each stored Act PDF, or with no --commit log what would change"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="write the legislation versions now",
    )
    arguments = parser.parse_args()
    apply_legislation_versions(arguments.commit)
