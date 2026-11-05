import argparse
from datetime import datetime, timezone
from functools import partial
from zoneinfo import ZoneInfo

from sqlmodel import Session

from crud.source import CRUDSource
from crud.source_response import CRUDSourceResponse
from database.harvest_run import HarvestRun
from database.init import create_db_and_tables, engine
from database.source import Source
from database.source_response import SourceResponse
from enums import ResponseKind, SourceName
from exceptions import OpenSgLawSourceRowError
from logs import logger
from populate.sso_responses import populate_sso_responses
from populate.written_tables import vacuum_analyze_written_tables
from settings import settings
from utils.write_target import validate_can_write

_SINGAPORE = ZoneInfo("Asia/Singapore")
_HTTP_OK = 200


def harvest_sso(is_commit: bool) -> None:
    if not is_commit:
        with Session(engine) as session:
            source = CRUDSource(session).get_by_name(SourceName.SSO)
            if source is None:
                raise OpenSgLawSourceRowError("The SSO source row is missing")
            stored_pdf_urls = CRUDSourceResponse(
                session
            ).get_requested_urls_by_source_and_kind_and_status_code_and_body_bytes_not_null(
                SourceName.SSO, ResponseKind.DOCUMENT, _HTTP_OK
            )
            logger.info(
                f"SSO is {source.sso_access_state}: {source.sso_access_state_reason}"
            )
            logger.info(
                f"It is {datetime.now(_SINGAPORE):%H:%M} SGT; requests go only from 03:00 to 06:55 SGT"
            )
            logger.info(f"{len(stored_pdf_urls):,} SSO PDFs are stored")
        logger.info("Dry run: nothing written")
        return
    validate_can_write(settings.database_url)
    create_db_and_tables()
    with Session(engine) as session:
        harvest_run = populate_sso_responses(
            session, partial(datetime.now, timezone.utc)
        )
        logger.info(
            f"SSO run {harvest_run.id} {harvest_run.status}: {harvest_run.requests_sent} sent,"
            f" {harvest_run.bodies_stored} stored, {harvest_run.bodies_unchanged} unchanged,"
            f" {harvest_run.failures} failed, halt reason {harvest_run.halt_reason}"
        )
        vacuum_analyze_written_tables(
            session,
            [
                SourceResponse.__tablename__,  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
                HarvestRun.__tablename__,  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
                Source.__tablename__,  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
            ],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Send one night's SSO requests, or with no --commit log the SSO state and send nothing"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="send SSO requests now; refused outside 03:00 to 06:55 SGT",
    )
    arguments = parser.parse_args()
    harvest_sso(arguments.commit)
