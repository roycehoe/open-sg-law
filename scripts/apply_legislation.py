import argparse

from sqlmodel import Session

from crud.legislation import CRUDLegislation
from database.init import engine
from database.legislation import Legislation
from exceptions import OpenSgLawWriteCheckError
from logs import logger
from populate.legislation import (
    LegislationWrite,
    get_legislation_write,
    write_legislation,
)
from populate.written_tables import vacuum_analyze_written_tables
from settings import settings
from utils.write_target import validate_can_write


def _log_write(legislation_write: LegislationWrite) -> None:
    logger.info(
        f"{len(legislation_write.legislations_to_insert):,} legislation rows to insert"
    )
    logger.info(
        f"{len(legislation_write.legislation_updates):,} legislation rows to update"
    )
    logger.info(f"{legislation_write.unchanged_count:,} legislation rows unchanged")
    for harvest_run_id in legislation_write.incomplete_harvest_run_ids:
        logger.info(f"Listing run {harvest_run_id} is incomplete and gives no rows")


def _validate_can_commit_legislation(session: Session, planned_count: int) -> None:
    stored_count = CRUDLegislation(session).get_count()
    if stored_count != planned_count:
        raise OpenSgLawWriteCheckError(
            f"{stored_count} legislation rows are stored, the plan has {planned_count}"
        )


def apply_legislation(is_commit: bool) -> None:
    if not is_commit:
        with Session(engine) as session:
            _log_write(get_legislation_write(session))
        logger.info("Dry run: nothing written")
        return
    validate_can_write(settings.database_url)
    with Session(engine) as session:
        legislation_write = get_legislation_write(session)
        _log_write(legislation_write)
        planned_count = CRUDLegislation(session).get_count() + len(
            legislation_write.legislations_to_insert
        )
        write_legislation(session, legislation_write)
        _validate_can_commit_legislation(session, planned_count)
        session.commit()
        logger.info("Committed")
        vacuum_analyze_written_tables(
            session,
            [Legislation.__tablename__],  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Store the Acts that the stored listing pages show, or with no --commit log what would change"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="write the legislation rows now",
    )
    arguments = parser.parse_args()
    apply_legislation(arguments.commit)
