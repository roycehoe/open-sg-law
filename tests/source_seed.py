from datetime import datetime
from typing import Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from crud.harvest_run import CRUDHarvestRun
from crud.source import CRUDSource
from crud.source_response import CRUDSourceResponse
from database.harvest_run import HarvestRun
from database.source import Source
from database.source_response import SourceResponse
from enums import (
    HarvestRunStatus,
    PublishStatus,
    ResponseKind,
    SourceName,
    SsoAccessState,
)
from schemas.source_http_response import SourceHttpResponse
from services.source_response import build_source_response

_PDF_CONTENT_TYPE = "application/pdf"
_PDF_BODY = b"%PDF-"


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


def build_source_http_answer(
    status_code: int, content_type: Optional[str], body: bytes
) -> SourceHttpResponse:
    return SourceHttpResponse(
        status_code=status_code,
        requested_url="",
        final_url="",
        content_type=content_type,
        body=body,
    )


def get_stored_source(engine: Engine, source_name: SourceName) -> Source:
    with Session(engine) as session:
        source = CRUDSource(session).get_by_name(source_name)
        assert source is not None
        return source


def get_harvest_runs(session: Session) -> list[HarvestRun]:
    return list(session.exec(select(HarvestRun)).all())


def get_source_responses(session: Session) -> list[SourceResponse]:
    return list(session.exec(select(SourceResponse)).all())


def seed_stored_pdf(
    session: Session, source_name: SourceName, started_at: datetime, pdf_url: str
) -> None:
    harvest_run = HarvestRun(
        source=source_name,
        status=HarvestRunStatus.SUCCEEDED,
        started_at=started_at,
    )
    CRUDHarvestRun(session).create(harvest_run)
    assert harvest_run.id is not None
    pdf_answer = build_source_http_answer(200, _PDF_CONTENT_TYPE, _PDF_BODY)
    CRUDSourceResponse(session).insert_on_conflict_do_nothing(
        build_source_response(
            pdf_answer.model_copy(
                update={"requested_url": pdf_url, "final_url": pdf_url}
            ),
            ResponseKind.DOCUMENT,
            source_name,
            harvest_run.id,
        )
    )
    session.commit()
