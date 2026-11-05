from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import Optional

from sqlmodel import Session

from crud.database_size import CRUDDatabaseSize
from crud.harvest_run import CRUDHarvestRun
from crud.source import CRUDSource
from crud.source_response import CRUDSourceResponse
from database.harvest_run import HarvestRun
from database.source import Source
from enums import (
    HarvestRunStatus,
    ResponseKind,
    SourceName,
    SsoAccessState,
    SsoAnswer,
)
from exceptions import (
    OpenSgLawGatewayError,
    OpenSgLawHarvestHaltError,
    OpenSgLawHarvestRunError,
    OpenSgLawSourceRowError,
    OpenSgLawSsoChallengeError,
    OpenSgLawSsoWindowError,
)
from gateway.sso import (
    get_sso_document_response,
    get_sso_listing_response,
    get_sso_robots_response,
)
from logs import logger
from schemas.source_http_response import SourceHttpResponse
from services.harvest_run import (
    get_stale_run_cutoff,
    validate_can_send_after_failures,
    validate_can_start_harvest_run,
    validate_can_store_at_database_size,
)
from services.source_response import (
    build_source_response,
    get_sso_listing_page_of_response,
)
from services.sso_answer import (
    get_sso_answer,
    is_sso_listing_page,
    is_sso_pdf,
    is_sso_robots_file,
)
from services.sso_request import (
    get_act_pdf_paths_to_fetch,
    validate_can_send_sso_request,
)
from utils.sso_listing import SsoListingRow

_HTTP_OK = 200
_FIRST_EXPECTED_ANSWER_REASON = "First expected answer"


@dataclass
class _NightProgress:
    consecutive_failure_count: int = 0


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
        f"SSO run {harvest_run.id} {status}: {harvest_run.requests_sent} sent,"
        f" {harvest_run.bodies_stored} stored, {harvest_run.bodies_unchanged} unchanged,"
        f" {harvest_run.failures} failed"
    )
    return harvest_run


def _record_failure(
    session: Session, harvest_run: HarvestRun, night_progress: _NightProgress
) -> None:
    harvest_run.failures += 1
    CRUDHarvestRun(session).update(harvest_run)
    night_progress.consecutive_failure_count += 1
    validate_can_send_after_failures(night_progress.consecutive_failure_count)


def _validate_can_store_more(session: Session) -> None:
    validate_can_store_at_database_size(
        CRUDDatabaseSize(session).get_current_database_bytes()
    )


def _store_response(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    source_http_response: SourceHttpResponse,
    kind: ResponseKind,
) -> None:
    harvest_run.requests_sent += 1
    is_stored = CRUDSourceResponse(session).insert_on_conflict_do_nothing(
        build_source_response(
            source_http_response, kind, SourceName.SSO, harvest_run_id
        )
    )
    if is_stored:
        harvest_run.bodies_stored += 1
        CRUDHarvestRun(session).update(harvest_run)
        return
    harvest_run.bodies_unchanged += 1
    CRUDHarvestRun(session).update(harvest_run)


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
        logger.warning(f"SSO request failed: {error}")
        _record_failure(session, harvest_run, night_progress)
        return None
    logger.info(
        f"SSO answered {source_http_response.status_code} with"
        f" {len(source_http_response.body):,} bytes to {source_http_response.requested_url}"
    )
    _store_response(session, harvest_run, harvest_run_id, source_http_response, kind)
    return source_http_response


def _mark_source_serving(
    session: Session, source: Source, clock: Callable[[], datetime]
) -> None:
    if source.sso_access_state != SsoAccessState.UNTESTED:
        return
    source.sso_access_state = SsoAccessState.SERVING
    source.sso_access_state_reason = _FIRST_EXPECTED_ANSWER_REASON
    source.sso_access_state_changed_at = clock()
    CRUDSource(session).update(source)
    session.commit()


def _send_sso_request(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    source: Source,
    night_progress: _NightProgress,
    send_request: Callable[[], SourceHttpResponse],
    kind: ResponseKind,
    is_expected_body: Callable[[SourceHttpResponse], bool],
    clock: Callable[[], datetime],
) -> Optional[SourceHttpResponse]:
    source_http_response = _send_and_store_request(
        session, harvest_run, harvest_run_id, night_progress, send_request, kind
    )
    if source_http_response is None:
        return None
    sso_answer = get_sso_answer(
        source_http_response, is_expected_body(source_http_response)
    )
    if sso_answer == SsoAnswer.FAILURE:
        _record_failure(session, harvest_run, night_progress)
        _validate_can_store_more(session)
        return None
    night_progress.consecutive_failure_count = 0
    _mark_source_serving(session, source, clock)
    _validate_can_store_more(session)
    return source_http_response


def _fetch_listing_rows(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    source: Source,
    night_progress: _NightProgress,
    validate_can_send: Callable[[], None],
    clock: Callable[[], datetime],
) -> Optional[list[SsoListingRow]]:
    first_listing_response = _send_sso_request(
        session,
        harvest_run,
        harvest_run_id,
        source,
        night_progress,
        partial(
            get_sso_listing_response,
            page_index=0,
            validate_can_send=validate_can_send,
        ),
        ResponseKind.LISTING_PAGE,
        is_sso_listing_page,
        clock,
    )
    if first_listing_response is None:
        return None
    first_listing_page = get_sso_listing_page_of_response(first_listing_response)
    listing_rows = list(first_listing_page.rows)
    for page_index in range(1, first_listing_page.page_count):
        listing_response = _send_sso_request(
            session,
            harvest_run,
            harvest_run_id,
            source,
            night_progress,
            partial(get_sso_listing_response, page_index, validate_can_send),
            ResponseKind.LISTING_PAGE,
            is_sso_listing_page,
            clock,
        )
        if listing_response is None:
            continue
        listing_rows.extend(get_sso_listing_page_of_response(listing_response).rows)
    return listing_rows


def _fetch_documents(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    source: Source,
    night_progress: _NightProgress,
    validate_can_send: Callable[[], None],
    clock: Callable[[], datetime],
    listing_rows: list[SsoListingRow],
) -> None:
    stored_document_urls = [
        *CRUDSourceResponse(
            session
        ).get_requested_urls_by_source_and_kind_and_status_code_and_body_bytes_not_null(
            SourceName.SSO, ResponseKind.DOCUMENT, _HTTP_OK
        ),
        *CRUDSourceResponse(
            session
        ).get_requested_urls_by_source_and_kind_and_status_code_and_body_bytes_not_null(
            SourceName.INTERNET_ARCHIVE, ResponseKind.DOCUMENT, _HTTP_OK
        ),
    ]
    for pdf_path in get_act_pdf_paths_to_fetch(listing_rows, stored_document_urls):
        _send_sso_request(
            session,
            harvest_run,
            harvest_run_id,
            source,
            night_progress,
            partial(get_sso_document_response, pdf_path, validate_can_send),
            ResponseKind.DOCUMENT,
            is_sso_pdf,
            clock,
        )


def _send_night_requests(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    source: Source,
    clock: Callable[[], datetime],
) -> None:
    night_progress = _NightProgress()
    validate_can_send = lambda: validate_can_send_sso_request(
        clock(), source.sso_access_state
    )
    _send_sso_request(
        session,
        harvest_run,
        harvest_run_id,
        source,
        night_progress,
        partial(get_sso_robots_response, validate_can_send),
        ResponseKind.ROBOTS_FILE,
        is_sso_robots_file,
        clock,
    )
    listing_rows = _fetch_listing_rows(
        session,
        harvest_run,
        harvest_run_id,
        source,
        night_progress,
        validate_can_send,
        clock,
    )
    if listing_rows is None:
        return
    _fetch_documents(
        session,
        harvest_run,
        harvest_run_id,
        source,
        night_progress,
        validate_can_send,
        clock,
        listing_rows,
    )


def populate_sso_responses(
    session: Session, clock: Callable[[], datetime]
) -> HarvestRun:
    started_at = clock()
    source = CRUDSource(session).get_by_name(SourceName.SSO)
    if source is None:
        raise OpenSgLawSourceRowError("The SSO source row is missing")
    validate_can_send_sso_request(started_at, source.sso_access_state)
    _validate_can_store_more(session)
    validate_can_start_harvest_run(
        CRUDHarvestRun(session).get_count_by_source_and_status_and_started_at_after(
            SourceName.SSO, HarvestRunStatus.RUNNING, get_stale_run_cutoff(started_at)
        ),
        SourceName.SSO,
    )
    harvest_run = HarvestRun(source=SourceName.SSO, started_at=started_at)
    CRUDHarvestRun(session).create(harvest_run)
    if harvest_run.id is None:
        raise OpenSgLawHarvestRunError("Run row has no id after commit")
    harvest_run_id = harvest_run.id
    try:
        _send_night_requests(session, harvest_run, harvest_run_id, source, clock)
    except OpenSgLawSsoWindowError:
        logger.info("The SSO window closed; the counts show what is left")
        return _finish_harvest_run(
            session, harvest_run, HarvestRunStatus.SUCCEEDED, clock()
        )
    except OpenSgLawSsoChallengeError as error:
        source.sso_access_state = SsoAccessState.CHALLENGED
        source.sso_access_state_reason = str(error)
        source.sso_access_state_changed_at = clock()
        CRUDSource(session).update(source)
        session.commit()
        harvest_run.halt_reason = str(error)
        return _finish_harvest_run(
            session, harvest_run, HarvestRunStatus.HALTED, clock()
        )
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
