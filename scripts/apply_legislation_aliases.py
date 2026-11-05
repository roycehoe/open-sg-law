import argparse

from sqlmodel import Session

from crud.legislation_alias import CRUDLegislationAlias
from database.init import engine
from database.legislation_alias import LegislationAlias
from exceptions import OpenSgLawWriteCheckError
from logs import logger
from populate.legislation_aliases import (
    LegislationAliasWrite,
    get_legislation_alias_write,
    write_legislation_aliases,
)
from populate.written_tables import vacuum_analyze_written_tables
from settings import settings
from utils.write_target import validate_can_write


def _log_write(legislation_alias_write: LegislationAliasWrite) -> None:
    logger.info(
        f"{len(legislation_alias_write.legislation_aliases_to_insert):,} legislation aliases to insert"
    )
    logger.info(
        f"{len(legislation_alias_write.legislation_alias_ids_to_delete):,} legislation aliases to delete"
    )
    logger.info(
        f"{legislation_alias_write.unchanged_count:,} legislation aliases unchanged"
    )


def _validate_can_commit_legislation_aliases(
    session: Session, planned_count: int
) -> None:
    stored_count = CRUDLegislationAlias(session).get_count()
    if stored_count != planned_count:
        raise OpenSgLawWriteCheckError(
            f"{stored_count} legislation aliases are stored, the plan has {planned_count}"
        )


def apply_legislation_aliases(is_commit: bool) -> None:
    if not is_commit:
        with Session(engine) as session:
            _log_write(get_legislation_alias_write(session))
        logger.info("Dry run: nothing written")
        return
    validate_can_write(settings.database_url)
    with Session(engine) as session:
        legislation_alias_write = get_legislation_alias_write(session)
        _log_write(legislation_alias_write)
        planned_count = legislation_alias_write.unchanged_count + len(
            legislation_alias_write.legislation_aliases_to_insert
        )
        write_legislation_aliases(session, legislation_alias_write)
        _validate_can_commit_legislation_aliases(session, planned_count)
        session.commit()
        logger.info("Committed")
        vacuum_analyze_written_tables(
            session,
            [LegislationAlias.__tablename__],  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Store the aliases of every stored Act's printed title and code, or with no --commit log what would change"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="write the legislation aliases now",
    )
    arguments = parser.parse_args()
    apply_legislation_aliases(arguments.commit)
