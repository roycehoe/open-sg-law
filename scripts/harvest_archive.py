import argparse
from datetime import datetime, timezone
from functools import partial

from sqlmodel import Session

from crud.source_response import CRUDSourceResponse
from database.harvest_run import HarvestRun
from database.init import create_db_and_tables, engine
from database.source_response import SourceResponse
from enums import ResponseKind, SourceName
from logs import logger
from populate.archive_responses import populate_archive_responses
from populate.written_tables import vacuum_analyze_written_tables
from settings import settings
from utils.write_target import validate_can_write

_HTTP_OK = 200


def harvest_archive(is_commit: bool) -> None:
    if not is_commit:
        with Session(engine) as session:
            stored_pdf_urls = CRUDSourceResponse(
                session
            ).get_requested_urls_by_source_and_kind_and_status_code_and_body_bytes_not_null(
                SourceName.INTERNET_ARCHIVE, ResponseKind.DOCUMENT, _HTTP_OK
            )
            stored_listing_capture_count = CRUDSourceResponse(
                session
            ).get_count_by_source_and_kind_and_status_code(
                SourceName.INTERNET_ARCHIVE, ResponseKind.LISTING_PAGE, _HTTP_OK
            )
            logger.info(f"{len(stored_pdf_urls):,} archive PDFs are stored")
            logger.info(
                f"{stored_listing_capture_count:,} archive listing captures are stored"
            )
        logger.info("Dry run: nothing written")
        return
    validate_can_write(settings.database_url)
    create_db_and_tables()
    with Session(engine) as session:
        harvest_run = populate_archive_responses(
            session, partial(datetime.now, timezone.utc)
        )
        logger.info(
            f"Archive run {harvest_run.id} {harvest_run.status}: {harvest_run.requests_sent} sent,"
            f" {harvest_run.bodies_stored} stored, {harvest_run.bodies_unchanged} unchanged,"
            f" {harvest_run.failures} failed, halt reason {harvest_run.halt_reason}"
        )
        vacuum_analyze_written_tables(
            session,
            [
                SourceResponse.__tablename__,  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
                HarvestRun.__tablename__,  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
            ],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch the Internet Archive's captures of the Act PDFs, or with no --commit log what is stored and send nothing"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="send Internet Archive requests now",
    )
    arguments = parser.parse_args()
    harvest_archive(arguments.commit)
