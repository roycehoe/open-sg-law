import argparse
from datetime import datetime, timezone

from sqlmodel import Session

from crud.source import CRUDSource
from database.init import engine
from database.source import Source
from enums import SourceName, SsoAccessState
from exceptions import (
    OpenSgLawReasonError,
    OpenSgLawSourceRowError,
    OpenSgLawSourceStateError,
)
from logs import logger
from populate.written_tables import vacuum_analyze_written_tables
from settings import settings
from utils.write_target import validate_can_write


def clear_sso_challenge(reason: str, is_commit: bool) -> None:
    if not reason.strip():
        raise OpenSgLawReasonError(
            "A clear needs a reason, such as the date of AGC's reply"
        )
    if is_commit:
        validate_can_write(settings.database_url)
    with Session(engine) as session:
        source = CRUDSource(session).get_by_name_for_update(SourceName.SSO)
        if source is None:
            raise OpenSgLawSourceRowError("The SSO source row is missing")
        if source.sso_access_state != SsoAccessState.CHALLENGED:
            raise OpenSgLawSourceStateError(
                f"SSO is {source.sso_access_state}, so there is no challenge to clear"
            )
        logger.info(
            f"SSO was challenged at {source.sso_access_state_changed_at}: {source.sso_access_state_reason}"
        )
        if not is_commit:
            logger.info("Dry run: nothing written")
            return
        source.sso_access_state = SsoAccessState.UNTESTED
        source.sso_access_state_reason = reason
        source.sso_access_state_changed_at = datetime.now(timezone.utc)
        CRUDSource(session).update(source)
        session.commit()
        logger.info("Committed")
        vacuum_analyze_written_tables(
            session,
            [Source.__tablename__],  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Set a CHALLENGED SSO source back to UNTESTED, with the reason it is cleared"
    )
    parser.add_argument(
        "--reason",
        required=True,
        help="why the challenge is cleared, such as the date of AGC's reply",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="write the change; without it the script only logs the challenge",
    )
    arguments = parser.parse_args()
    clear_sso_challenge(arguments.reason, arguments.commit)
