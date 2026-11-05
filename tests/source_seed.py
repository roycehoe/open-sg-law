from sqlmodel import Session

from database.source import Source
from enums import PublishStatus, SourceName, SsoAccessState


def seed_sources(session: Session) -> None:
    session.add_all(
        (
            Source(
                name=SourceName.SSO,
                publish_status=PublishStatus.PUBLISHED,
                sso_access_state=SsoAccessState.UNTESTED,
            ),
            Source(
                name=SourceName.INTERNET_ARCHIVE,
                publish_status=PublishStatus.PUBLISHED,
            ),
            Source(name=SourceName.EGAZETTE, publish_status=PublishStatus.PUBLISHED),
            Source(name=SourceName.DATA_GOV_SG, publish_status=PublishStatus.PUBLISHED),
            Source(
                name=SourceName.ELITIGATION, publish_status=PublishStatus.UNPUBLISHED
            ),
            Source(
                name=SourceName.OPENHANSARD_LINKS,
                publish_status=PublishStatus.PUBLISHED,
            ),
        )
    )
    session.commit()
