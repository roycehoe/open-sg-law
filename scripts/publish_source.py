import argparse
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlmodel import Session

from crud.source import CRUDSource
from crud.source_grant import CRUDSourceGrant
from database.init import engine
from database.source import Source
from enums import PublishStatus, SourceName
from exceptions import OpenSgLawSourceRowError, OpenSgLawSourceStateError
from logs import logger
from populate.written_tables import vacuum_analyze_written_tables
from services.source_grants import SITE_ROLE_NAME, get_table_names_to_grant
from settings import settings
from utils.reason import validate_can_record_reason
from utils.write_target import validate_can_write

_SELECT_PRIVILEGE = "SELECT"
_PUBLIC_SCHEMA = "public"


@dataclass(frozen=True)
class _SiteGrantChange:
    table_names_to_grant: list[str]
    table_names_to_revoke: list[str]


def _get_published_sources(
    sources: list[Source], source_name: SourceName, publish_status: PublishStatus
) -> frozenset[SourceName]:
    source_name_to_publish_status = {
        **{
            SourceName(source.name): PublishStatus(source.publish_status)
            for source in sources
        },
        source_name: publish_status,
    }
    return frozenset(
        name
        for name, status in source_name_to_publish_status.items()
        if status == PublishStatus.PUBLISHED
    )


def _get_site_grant_change(
    session: Session, published_sources: frozenset[SourceName]
) -> _SiteGrantChange:
    table_names_to_grant = get_table_names_to_grant(published_sources)
    granted_table_names = CRUDSourceGrant(
        session
    ).get_table_names_by_grantee_and_privilege_type_and_table_schema(
        SITE_ROLE_NAME, _SELECT_PRIVILEGE, _PUBLIC_SCHEMA
    )
    return _SiteGrantChange(
        table_names_to_grant=[
            table_name
            for table_name in table_names_to_grant
            if table_name not in granted_table_names
        ],
        table_names_to_revoke=[
            table_name
            for table_name in granted_table_names
            if table_name not in table_names_to_grant
        ],
    )


def _log_site_grant_change(site_grant_change: _SiteGrantChange) -> None:
    for table_name in site_grant_change.table_names_to_grant:
        logger.info(f"Would grant SELECT on {table_name} to {SITE_ROLE_NAME}")
    for table_name in site_grant_change.table_names_to_revoke:
        logger.info(f"Would revoke SELECT on {table_name} from {SITE_ROLE_NAME}")


def _sync_site_grants(session: Session, site_grant_change: _SiteGrantChange) -> None:
    for table_name in site_grant_change.table_names_to_grant:
        CRUDSourceGrant(session).grant_select(
            _PUBLIC_SCHEMA, table_name, SITE_ROLE_NAME
        )
        logger.info(f"Granted SELECT on {table_name} to {SITE_ROLE_NAME}")
    for table_name in site_grant_change.table_names_to_revoke:
        CRUDSourceGrant(session).revoke_select(
            _PUBLIC_SCHEMA, table_name, SITE_ROLE_NAME
        )
        logger.info(f"Revoked SELECT on {table_name} from {SITE_ROLE_NAME}")


def publish_source(
    source_name: SourceName,
    reason: str,
    publish_status: PublishStatus,
    is_commit: bool,
) -> None:
    validate_can_record_reason(
        reason,
        "A change of publish status",
        "the date of the permission letter or why it is withdrawn",
    )
    if is_commit:
        validate_can_write(settings.database_url)
    with Session(engine) as session:
        sources = CRUDSource(session).get_all_for_update()
        source_name_to_source = {
            SourceName(stored_source.name): stored_source for stored_source in sources
        }
        source = source_name_to_source.get(source_name)
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
        site_grant_change = _get_site_grant_change(
            session,
            _get_published_sources(sources, source_name, publish_status),
        )
        if not is_commit:
            _log_site_grant_change(site_grant_change)
            logger.info("Dry run: nothing written")
            return
        source.publish_status = publish_status
        source.publish_status_reason = reason
        source.publish_status_changed_at = datetime.now(timezone.utc)
        CRUDSource(session).update(source)
        _sync_site_grants(session, site_grant_change)
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
        PublishStatus.UNPUBLISHED if arguments.withdraw else PublishStatus.PUBLISHED,
        arguments.commit,
    )
