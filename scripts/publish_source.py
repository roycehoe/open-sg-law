import argparse
from datetime import datetime, timezone

from sqlmodel import Session

from crud.source import CRUDSource
from database.init import engine
from database.source import Source
from enums import PublishStatus, SourceName
from exceptions import (
    OpenSgLawReasonError,
    OpenSgLawSourceRowError,
    OpenSgLawSourceStateError,
)
from logs import logger
from populate.written_tables import vacuum_analyze_written_tables
from settings import settings
from utils.write_target import validate_can_write


def publish_source(
    source_name: SourceName, reason: str, is_withdrawal: bool, is_commit: bool
) -> None:
    if not reason.strip():
        raise OpenSgLawReasonError(
            "A change of publish status needs a reason, such as the date of the permission letter or why it is withdrawn"
        )
    if is_commit:
        validate_can_write(settings.database_url)
    publish_status = (
        PublishStatus.UNPUBLISHED if is_withdrawal else PublishStatus.PUBLISHED
    )
    with Session(engine) as session:
        source = CRUDSource(session).get_by_name_for_update(source_name)
        if source is None:
            raise OpenSgLawSourceRowError(
                f"The {source_name.value} source row is missing"
            )
        if source.publish_status == publish_status:
            raise OpenSgLawSourceStateError(
                f"{source_name.value} is already {publish_status.value}"
            )
        logger.info(
            f"{source_name.value} goes from {source.publish_status} to {publish_status.value}: {reason}"
        )
        if not is_commit:
            logger.info("Dry run: nothing written")
            return
        source.publish_status = publish_status
        source.publish_status_reason = reason
        source.publish_status_changed_at = datetime.now(timezone.utc)
        CRUDSource(session).update(source)
        session.commit()
        logger.info("Committed")
        vacuum_analyze_written_tables(
            session,
            [Source.__tablename__],  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Publish a source, or withdraw it with --withdraw, with the reason for the change"
    )
    parser.add_argument(
        "--source",
        required=True,
        choices=[source_name.value for source_name in SourceName],
        help="the source whose publish status changes",
    )
    parser.add_argument(
        "--reason",
        required=True,
        help="why the status changes, such as the date of the permission letter or why it is withdrawn",
    )
    parser.add_argument(
        "--withdraw",
        action="store_true",
        help="set the source UNPUBLISHED instead of PUBLISHED",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="write the change; without it the script only logs it",
    )
    arguments = parser.parse_args()
    publish_source(
        SourceName(arguments.source),
        arguments.reason,
        arguments.withdraw,
        arguments.commit,
    )
