from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlmodel import Session

from crud.harvest_run import CRUDHarvestRun
from crud.source_response import CRUDSourceResponse, ListingPageRow
from database.harvest_run import HarvestRun
from enums import HarvestRunStatus, ResponseKind, SourceName
from schemas.source_http_response import SourceHttpResponse
from services.source_response import build_source_response
from utils.archive_capture_url import build_archive_capture_url
from utils.sso_listing import build_sso_listing_url

LISTING_CONTENT_TYPE = "text/html; charset=utf-8"
_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures" / "sso_listing"
FIRST_PAGE_BODY = (
    _FIXTURES_DIRECTORY / "browse-all-p1-20240716-trimmed.html"
).read_bytes()
SECOND_PAGE_BODY = (
    _FIXTURES_DIRECTORY / "browse-all-p2-20240719-trimmed.html"
).read_bytes()
_FIRST_CAPTURE_TIMESTAMP = "20240716234218"
_SECOND_CAPTURE_TIMESTAMP = "20240719042908"


def build_listing_page_row(
    page_id: int,
    harvest_run_id: int,
    source: SourceName,
    page_index: int,
    body_text: Optional[str],
    capture_timestamp: str,
    fetched_at: datetime,
) -> ListingPageRow:
    sso_url = build_sso_listing_url(page_index)
    requested_url = (
        build_archive_capture_url(capture_timestamp, sso_url)
        if source == SourceName.INTERNET_ARCHIVE
        else sso_url
    )
    return ListingPageRow(
        id=page_id,
        requested_url=requested_url,
        final_url=requested_url,
        content_type=LISTING_CONTENT_TYPE,
        body_text=body_text,
        fetched_at=fetched_at,
        source=source,
        harvest_run_id=harvest_run_id,
    )


def build_listing_page_rows(
    harvest_run_id: int,
    source: SourceName,
    fetched_at: datetime,
    page_indexes: tuple[int, ...] = (0, 1),
) -> list[ListingPageRow]:
    page_index_to_body = {
        0: FIRST_PAGE_BODY.decode("utf-8"),
        1: SECOND_PAGE_BODY.decode("utf-8"),
    }
    page_index_to_timestamp = {
        0: _FIRST_CAPTURE_TIMESTAMP,
        1: _SECOND_CAPTURE_TIMESTAMP,
    }
    return [
        build_listing_page_row(
            page_id=harvest_run_id * 10 + page_index,
            harvest_run_id=harvest_run_id,
            source=source,
            page_index=page_index,
            body_text=page_index_to_body[page_index],
            capture_timestamp=page_index_to_timestamp[page_index],
            fetched_at=fetched_at,
        )
        for page_index in page_indexes
    ]


def seed_listing(
    session: Session,
    source: SourceName,
    fetched_at: datetime,
    page_indexes: tuple[int, ...] = (0, 1),
) -> None:
    harvest_run = HarvestRun(
        source=source, status=HarvestRunStatus.SUCCEEDED, started_at=fetched_at
    )
    CRUDHarvestRun(session).create(harvest_run)
    assert harvest_run.id is not None
    for page_row in build_listing_page_rows(
        harvest_run.id, source, fetched_at, page_indexes
    ):
        source_response = build_source_response(
            SourceHttpResponse(
                status_code=200,
                requested_url=page_row.requested_url,
                final_url=page_row.final_url,
                content_type=page_row.content_type,
                body=(page_row.body_text or "").encode("utf-8"),
            ),
            ResponseKind.LISTING_PAGE,
            source,
            harvest_run.id,
        )
        source_response.fetched_at = fetched_at
        CRUDSourceResponse(session).insert_on_conflict_do_nothing(source_response)
    session.commit()
