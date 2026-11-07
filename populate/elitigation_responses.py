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
    OpenSgLawGatewayError,
    OpenSgLawHarvestHaltError,
    OpenSgLawHarvestRunError,
    OpenSgLawListingParseError,
)
from gateway.elitigation import (
    get_elitigation_judgment_response,
    get_elitigation_listing_response,
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
    get_body_text,
    get_elitigation_listing_page_of_response,
)
from settings import settings
from utils.elitigation_judgment import get_elitigation_neutral_citation

_COURT_FILTER = "SUPCT"
_FIRST_YEAR = 1965
_FIRST_PAGE_NUMBER = 1
_NEUTRAL_CITATION_MARKER = "<title>["
_BODIES_PER_COMMIT = 100
_HTTP_OK = 200


@dataclass(frozen=True)
class _YearListing:
    result_count: int
    judgment_urls: list[str]


@dataclass
class _RunProgress:
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
        f"eLitigation run {harvest_run.id} {status}: {harvest_run.requests_sent} sent,"
        f" {harvest_run.bodies_stored} stored, {harvest_run.bodies_unchanged} unchanged,"
        f" {harvest_run.failures} failed"
    )
    return harvest_run


def _validate_can_store_more(session: Session) -> None:
    validate_can_store_at_database_size(
        CRUDDatabaseSize(session).get_current_database_bytes()
    )


def _commit_progress(
    session: Session, harvest_run: HarvestRun, run_progress: _RunProgress
) -> None:
    CRUDHarvestRun(session).update(harvest_run)
    _validate_can_store_more(session)
    run_progress.bodies_since_commit = 0


def _store_response(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    run_progress: _RunProgress,
    source_http_response: SourceHttpResponse,
    kind: ResponseKind,
) -> None:
    harvest_run.requests_sent += 1
    is_stored = CRUDSourceResponse(session).insert_on_conflict_do_nothing(
        build_source_response(
            source_http_response, kind, SourceName.ELITIGATION, harvest_run_id
        )
    )
    if is_stored:
        harvest_run.bodies_stored += 1
    else:
        harvest_run.bodies_unchanged += 1
    run_progress.bodies_since_commit += 1
    if run_progress.bodies_since_commit == _BODIES_PER_COMMIT:
        _commit_progress(session, harvest_run, run_progress)


def _record_failure(
    session: Session, harvest_run: HarvestRun, run_progress: _RunProgress
) -> None:
    harvest_run.failures += 1
    CRUDHarvestRun(session).update(harvest_run)
    run_progress.consecutive_failure_count += 1
    validate_can_send_after_failures(run_progress.consecutive_failure_count)


def _fetch_elitigation_response(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    run_progress: _RunProgress,
    send_request: Callable[[], SourceHttpResponse],
    kind: ResponseKind,
    is_expected_body: Callable[[SourceHttpResponse], bool],
) -> Optional[SourceHttpResponse]:
    try:
        source_http_response = send_request()
    except OpenSgLawGatewayError as error:
        logger.warning(f"eLitigation request failed: {error}")
        _record_failure(session, harvest_run, run_progress)
        return None
    logger.info(
        f"eLitigation answered {source_http_response.status_code} with"
        f" {len(source_http_response.body):,} bytes to {source_http_response.requested_url}"
    )
    _store_response(
        session,
        harvest_run,
        harvest_run_id,
        run_progress,
        source_http_response,
        kind,
    )
    if source_http_response.status_code != _HTTP_OK:
        _record_failure(session, harvest_run, run_progress)
        return None
    if not is_expected_body(source_http_response):
        _record_failure(session, harvest_run, run_progress)
        return None
    run_progress.consecutive_failure_count = 0
    return source_http_response


def _is_listing_page(source_http_response: SourceHttpResponse) -> bool:
    try:
        get_elitigation_listing_page_of_response(source_http_response)
    except OpenSgLawListingParseError:
        return False
    return True


def _has_neutral_citation(source_http_response: SourceHttpResponse) -> bool:
    judgment_text = get_body_text(
        source_http_response.body, source_http_response.content_type
    )
    if judgment_text is None:
        return False
    return get_elitigation_neutral_citation(judgment_text) is not None


def _fetch_year_judgment_urls(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    run_progress: _RunProgress,
    year: int,
) -> Optional[_YearListing]:
    first_listing_response = _fetch_elitigation_response(
        session,
        harvest_run,
        harvest_run_id,
        run_progress,
        partial(
            get_elitigation_listing_response,
            _COURT_FILTER,
            year,
            _FIRST_PAGE_NUMBER,
        ),
        ResponseKind.LISTING_PAGE,
        _is_listing_page,
    )
    if first_listing_response is None:
        return None
    first_listing_page = get_elitigation_listing_page_of_response(
        first_listing_response
    )
    judgment_paths = [row.judgment_path for row in first_listing_page.rows]
    for page_number in range(_FIRST_PAGE_NUMBER + 1, first_listing_page.page_count + 1):
        listing_response = _fetch_elitigation_response(
            session,
            harvest_run,
            harvest_run_id,
            run_progress,
            partial(get_elitigation_listing_response, _COURT_FILTER, year, page_number),
            ResponseKind.LISTING_PAGE,
            _is_listing_page,
        )
        if listing_response is None:
            continue
        judgment_paths.extend(
            row.judgment_path
            for row in get_elitigation_listing_page_of_response(listing_response).rows
        )
    return _YearListing(
        result_count=first_listing_page.result_count,
        judgment_urls=[
            f"{settings.elitigation_base_url}{judgment_path}"
            for judgment_path in dict.fromkeys(judgment_paths)
        ],
    )


def _fetch_year(
    session: Session,
    harvest_run: HarvestRun,
    harvest_run_id: int,
    run_progress: _RunProgress,
    stored_judgment_urls: set[str],
    year: int,
) -> None:
    year_listing = _fetch_year_judgment_urls(
        session, harvest_run, harvest_run_id, run_progress, year
    )
    if year_listing is None:
        logger.info(f"{year}: the first listing page was not read")
        return
    for judgment_url in year_listing.judgment_urls:
        if judgment_url in stored_judgment_urls:
            continue
        judgment_response = _fetch_elitigation_response(
            session,
            harvest_run,
            harvest_run_id,
            run_progress,
            partial(get_elitigation_judgment_response, judgment_url),
            ResponseKind.DOCUMENT,
            _has_neutral_citation,
        )
        if judgment_response is not None:
            stored_judgment_urls.add(judgment_url)
    stored_count = len(stored_judgment_urls.intersection(year_listing.judgment_urls))
    logger.info(
        f"{year}: {stored_count} of {year_listing.result_count} judgments stored"
    )


def populate_elitigation_responses(
    session: Session, clock: Callable[[], datetime]
) -> HarvestRun:
    started_at = clock()
    _validate_can_store_more(session)
    validate_can_start_harvest_run(
        CRUDHarvestRun(session).get_count_by_source_and_status_and_started_at_after(
            SourceName.ELITIGATION,
            HarvestRunStatus.RUNNING,
            get_stale_run_cutoff(started_at),
        ),
        SourceName.ELITIGATION,
    )
    harvest_run = HarvestRun(source=SourceName.ELITIGATION, started_at=started_at)
    CRUDHarvestRun(session).create(harvest_run)
    if harvest_run.id is None:
        raise OpenSgLawHarvestRunError("Run row has no id after commit")
    harvest_run_id = harvest_run.id
    run_progress = _RunProgress()
    stored_judgment_urls = set(
        CRUDSourceResponse(
            session
        ).get_requested_urls_by_source_and_kind_and_status_code_and_body_text_contains(
            SourceName.ELITIGATION,
            ResponseKind.DOCUMENT,
            _HTTP_OK,
            _NEUTRAL_CITATION_MARKER,
        )
    )
    try:
        for year in range(started_at.year, _FIRST_YEAR - 1, -1):
            _fetch_year(
                session,
                harvest_run,
                harvest_run_id,
                run_progress,
                stored_judgment_urls,
                year,
            )
        _commit_progress(session, harvest_run, run_progress)
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
