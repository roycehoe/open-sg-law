from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Optional

from sqlmodel import Session

from crud.database_size import CRUDDatabaseSize
from crud.harvest_run import CRUDHarvestRun
from crud.source_response import CRUDSourceResponse
from database.harvest_run import HarvestRun
from enums import HarvestRunStatus, ResponseKind, SourceName
from exceptions import (
    OpenSgLawCdxAnswerError,
    OpenSgLawGatewayError,
    OpenSgLawHarvestHaltError,
    OpenSgLawHarvestRunError,
    OpenSgLawListingParseError,
)
from gateway.internet_archive import (
    get_archive_capture_response,
    get_archive_cdx_response,
)
from logs import logger
from schemas.source_http_response import SourceHttpResponse
from services.archive_capture import (
    CdxCapture,
    get_cdx_captures,
    get_latest_act_captures,
)
from services.harvest_run import (
    get_stale_run_cutoff,
    validate_can_send_after_failures,
    validate_can_start_harvest_run,
    validate_can_store_at_database_size,
)
from services.source_response import (
    build_source_response,
    get_body_text,
    get_sso_listing_page_of_response,
)
from utils.archive_capture_url import (
    CAPTURE_TIMESTAMP_FORMAT,
    build_archive_capture_url,
)
from utils.sso_listing import (
    build_sso_listing_url,
)

_ACT_URL_PREFIX = "sso.agc.gov.sg/Act"
_PDF_MIME_TYPE = "application/pdf"
_BODIES_PER_COMMIT = 100
_HTTP_OK = 200
_HTTP_NOT_FOUND = 404
_PDF_SIGNATURE = b"%PDF-"


@dataclass
class _NightProgress:
    consecutive_failure_count: int = 0
    bodies_since_commit: int = 0


def _finish_harvest_run(
    session: Session,
    harvest_run: HarvestRun,
    status: HarvestRunStatus,
    finished_at: datetime,
) -> HarvestRun:
    harvest_run.status = status
    harvest_run.finished_at = finished_at
    CRUDHarvestRun(session).update(harvest_run)
    logger.info(
        f"Archive run {harvest_run.id} {status}: {harvest_run.requests_sent} sent,"
        f" {harvest_run.bodies_stored} stored, {harvest_run.bodies_unchanged} unchanged,"
        f" {harvest_run.failures} failed"
    )
    return harvest_run


def _validate_can_store_more(session: Session) -> None:
    validate_can_store_at_database_size(
        CRUDDatabaseSize(session).get_current_database_bytes()
    )


def _commit_progress(
    session: Session, harvest_run: HarvestRun, night_progress: _NightProgress
) -> None:
    CRUDHarvestRun(session).update(harvest_run)
    _validate_can_store_more(session)
    night_progress.bodies_since_commit = 0


def _store_response(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    night_progress: _NightProgress,
    source_http_response: SourceHttpResponse,
    kind: ResponseKind,
) -> None:
    harvest_run.requests_sent += 1
    is_stored = CRUDSourceResponse(session).insert_on_conflict_do_nothing(
        build_source_response(
            source_http_response, kind, SourceName.INTERNET_ARCHIVE, harvest_run_id
        )
    )
    if is_stored:
        harvest_run.bodies_stored += 1
    else:
        harvest_run.bodies_unchanged += 1
    night_progress.bodies_since_commit += 1
    if night_progress.bodies_since_commit == _BODIES_PER_COMMIT:
        _commit_progress(session, harvest_run, night_progress)


def _record_failure(
    session: Session, harvest_run: HarvestRun, night_progress: _NightProgress
) -> None:
    harvest_run.failures += 1
    CRUDHarvestRun(session).update(harvest_run)
    night_progress.consecutive_failure_count += 1
    validate_can_send_after_failures(night_progress.consecutive_failure_count)


def _send_and_store_request(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    night_progress: _NightProgress,
    send_request: Callable[[], SourceHttpResponse],
    kind: ResponseKind,
) -> Optional[SourceHttpResponse]:
    try:
        source_http_response = send_request()
    except OpenSgLawGatewayError as error:
        logger.warning(f"Archive request failed: {error}")
        _record_failure(session, harvest_run, night_progress)
        return None
    logger.info(
        f"Archive answered {source_http_response.status_code} with"
        f" {len(source_http_response.body):,} bytes to {source_http_response.requested_url}"
    )
    _store_response(
        session,
        harvest_run,
        harvest_run_id,
        night_progress,
        source_http_response,
        kind,
    )
    return source_http_response


def _fetch_archive_response(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    night_progress: _NightProgress,
    send_request: Callable[[], SourceHttpResponse],
    kind: ResponseKind,
    is_expected_body: Callable[[SourceHttpResponse], bool],
) -> Optional[SourceHttpResponse]:
    source_http_response = _send_and_store_request(
        session, harvest_run, harvest_run_id, night_progress, send_request, kind
    )
    if source_http_response is None:
        return None
    if source_http_response.status_code != _HTTP_OK:
        _record_failure(session, harvest_run, night_progress)
        return None
    if not is_expected_body(source_http_response):
        _record_failure(session, harvest_run, night_progress)
        return None
    night_progress.consecutive_failure_count = 0
    return source_http_response


def _is_pdf(source_http_response: SourceHttpResponse) -> bool:
    return source_http_response.body.startswith(_PDF_SIGNATURE)


def _is_listing_page(source_http_response: SourceHttpResponse) -> bool:
    try:
        get_sso_listing_page_of_response(source_http_response)
    except OpenSgLawListingParseError:
        return False
    return True


def _fetch_listing_captures(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    night_progress: _NightProgress,
    capture_timestamp: str,
) -> None:
    first_listing_response = _fetch_archive_response(
        session,
        harvest_run,
        harvest_run_id,
        night_progress,
        partial(
            get_archive_capture_response,
            capture_timestamp,
            build_sso_listing_url(page_index=0),
        ),
        ResponseKind.LISTING_PAGE,
        _is_listing_page,
    )
    if first_listing_response is None:
        return
    for page_index in range(
        1, get_sso_listing_page_of_response(first_listing_response).page_count
    ):
        _fetch_archive_response(
            session,
            harvest_run,
            harvest_run_id,
            night_progress,
            partial(
                get_archive_capture_response,
                capture_timestamp,
                build_sso_listing_url(page_index),
            ),
            ResponseKind.LISTING_PAGE,
            _is_listing_page,
        )


def _fetch_latest_act_captures(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    night_progress: _NightProgress,
) -> list[CdxCapture]:
    cdx_response = _send_and_store_request(
        session,
        harvest_run,
        harvest_run_id,
        night_progress,
        partial(get_archive_cdx_response, _ACT_URL_PREFIX, _PDF_MIME_TYPE),
        ResponseKind.CDX_ANSWER,
    )
    if cdx_response is None:
        raise OpenSgLawHarvestHaltError("The CDX query got no answer")
    _commit_progress(session, harvest_run, night_progress)
    if cdx_response.status_code != _HTTP_OK:
        raise OpenSgLawHarvestHaltError(
            f"The CDX query answered {cdx_response.status_code}"
        )
    cdx_answer_text = get_body_text(cdx_response.body, cdx_response.content_type)
    if cdx_answer_text is None:
        raise OpenSgLawHarvestHaltError("The CDX answer is not text")
    try:
        cdx_captures = get_cdx_captures(cdx_answer_text)
    except OpenSgLawCdxAnswerError as error:
        raise OpenSgLawHarvestHaltError(str(error)) from error
    return get_latest_act_captures(cdx_captures)


def _fetch_act_captures(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    night_progress: _NightProgress,
    is_retry_not_found: bool,
) -> None:
    latest_captures = _fetch_latest_act_captures(
        session, harvest_run, harvest_run_id, night_progress
    )
    stored_capture_urls = set(
        CRUDSourceResponse(
            session
        ).get_requested_urls_by_source_and_kind_and_status_code_and_body_bytes_not_null(
            SourceName.INTERNET_ARCHIVE, ResponseKind.DOCUMENT, _HTTP_OK
        )
    )
    if not is_retry_not_found:
        stored_capture_urls.update(
            CRUDSourceResponse(session).get_requested_urls_by_source_and_kind_and_status_code(
                SourceName.INTERNET_ARCHIVE, ResponseKind.DOCUMENT, _HTTP_NOT_FOUND
            )
        )
    skipped_capture_count = 0
    for capture in latest_captures:
        capture_url = build_archive_capture_url(capture.timestamp, capture.original_url)
        if capture_url in stored_capture_urls:
            skipped_capture_count += 1
            continue
        _fetch_archive_response(
            session,
            harvest_run,
            harvest_run_id,
            night_progress,
            partial(
                get_archive_capture_response, capture.timestamp, capture.original_url
            ),
            ResponseKind.DOCUMENT,
            _is_pdf,
        )
    logger.info(
        f"{skipped_capture_count} of {len(latest_captures)} latest Act captures"
        " were already stored"
    )


def populate_archive_responses(
    session: Session, clock: Callable[[], datetime], is_retry_not_found: bool = False
) -> HarvestRun:
    started_at = clock()
    _validate_can_store_more(session)
    validate_can_start_harvest_run(
        CRUDHarvestRun(session).get_count_by_source_and_status_and_started_at_after(
            SourceName.INTERNET_ARCHIVE,
            HarvestRunStatus.RUNNING,
            get_stale_run_cutoff(started_at),
        ),
        SourceName.INTERNET_ARCHIVE,
    )
    harvest_run = HarvestRun(source=SourceName.INTERNET_ARCHIVE, started_at=started_at)
    CRUDHarvestRun(session).create(harvest_run)
    if harvest_run.id is None:
        raise OpenSgLawHarvestRunError("Run row has no id after commit")
    harvest_run_id = harvest_run.id
    night_progress = _NightProgress()
    try:
        _fetch_listing_captures(
            session,
            harvest_run,
            harvest_run_id,
            night_progress,
            clock().strftime(CAPTURE_TIMESTAMP_FORMAT),
        )
        _fetch_act_captures(session, harvest_run, harvest_run_id, night_progress, is_retry_not_found)
        _commit_progress(session, harvest_run, night_progress)
    except OpenSgLawHarvestHaltError as error:
        harvest_run.halt_reason = str(error)
        return _finish_harvest_run(
            session, harvest_run, HarvestRunStatus.HALTED, clock()
        )
    except BaseException as unexpected_failure:  # noqa: BLE001 the run row records the failure before it propagates
        session.rollback()
        harvest_run.failure_reason = type(unexpected_failure).__name__
        _finish_harvest_run(session, harvest_run, HarvestRunStatus.FAILED, clock())
        raise
    return _finish_harvest_run(
        session, harvest_run, HarvestRunStatus.SUCCEEDED, clock()
    )
