import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

import populate.archive_responses as archive_responses_stage
from crud.database_size import CRUDDatabaseSize
from crud.harvest_run import CRUDHarvestRun
from database.harvest_run import HarvestRun
from enums import HarvestRunStatus, ResponseKind, SourceName
from exceptions import (
    OpenSgLawGatewayError,
    OpenSgLawHarvestHaltError,
    OpenSgLawHarvestRunError,
)
from populate.archive_responses import populate_archive_responses
from schemas.source_http_response import SourceHttpResponse
from tests.listing_seed import FIRST_PAGE_BODY, LISTING_CONTENT_TYPE, SECOND_PAGE_BODY
from tests.source_seed import (
    build_source_http_answer,
    get_harvest_runs,
    get_source_responses,
    seed_sources,
    seed_stored_pdf,
)
from utils.archive_capture_url import build_archive_capture_url
from utils.sso_listing import build_sso_listing_url

_RUN_TIME = datetime(2026, 11, 6, 19, 0, tzinfo=timezone.utc)
_CAPTURE_TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"
_DATABASE_HALT_BYTES = 10 * 1_024**3
_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"
_CLTPA_ANSWER_BODY = (
    _FIXTURES_DIRECTORY / "cdx" / "cdx-cltpa-pdf-trimmed.json"
).read_bytes()
_OFFLINE_PAGE_BODY = (
    _FIXTURES_DIRECTORY / "archive" / "temporarily-offline-20261104.html"
).read_bytes()
_CDX_CONTENT_TYPE = "application/json"
_PDF_CONTENT_TYPE = "application/pdf"
_PDF_BODY = b"%PDF-"
_NOT_FOUND_BODY = b"<html><body>Page not found</body></html>"
_ACT_URL_PREFIX = "sso.agc.gov.sg/Act"
_PDF_MIME_TYPE = "application/pdf"
_ACT_BASE_URL = "https://sso.agc.gov.sg/Act/"
_AA1906_URL = f"{_ACT_BASE_URL}AA1906?ViewType=Pdf&_=20240203013120"
_AA2001_EARLIER_URL = f"{_ACT_BASE_URL}AA2001?ViewType=Pdf&_=20231229163706"
_AA2001_LATER_URL = f"{_ACT_BASE_URL}AA2001?ViewType=Pdf&_=20250403160141"
_AA2004_URL = f"{_ACT_BASE_URL}AA2004?ViewType=Pdf&_=20251128173458"
_AA2020_URL = f"{_ACT_BASE_URL}AA2020?ViewType=Pdf&_=20250509132901"
_CDX_HEADER = ["original", "timestamp", "digest"]
_CDX_ROWS = [
    [_AA1906_URL, "20251231140314", ""],
    [_AA2001_EARLIER_URL, "20250430031007", ""],
    [_AA2001_LATER_URL, "20251231140335", ""],
    [_AA2004_URL, "20251231140429", ""],
    [_AA2020_URL, "20251231140443", ""],
]
_LATEST_ACT_CAPTURES = (
    (_AA1906_URL, "20251231140314"),
    (_AA2001_LATER_URL, "20251231140335"),
    (_AA2004_URL, "20251231140429"),
    (_AA2020_URL, "20251231140443"),
)
_LISTING_URLS = (build_sso_listing_url(0), build_sso_listing_url(1))
_FULL_RUN_REQUEST_COUNT = 7
_LISTING_REQUEST_COUNT = 2
_FAILURE_HALT_COUNT = 3
_COMMIT_EVERY_TWO_BODIES = 2


_FIRST_LISTING_ANSWER = build_source_http_answer(
    200, LISTING_CONTENT_TYPE, FIRST_PAGE_BODY
)
_SECOND_LISTING_ANSWER = build_source_http_answer(
    200, LISTING_CONTENT_TYPE, SECOND_PAGE_BODY
)
_PDF_ANSWER = build_source_http_answer(200, _PDF_CONTENT_TYPE, _PDF_BODY)
_NOT_FOUND_ANSWER = build_source_http_answer(404, "text/html", _NOT_FOUND_BODY)
_CDX_ANSWER = build_source_http_answer(
    200,
    _CDX_CONTENT_TYPE,
    json.dumps([_CDX_HEADER, *_CDX_ROWS]).encode(),
)
_CLTPA_ANSWER = build_source_http_answer(200, _CDX_CONTENT_TYPE, _CLTPA_ANSWER_BODY)
_OFFLINE_ANSWER = build_source_http_answer(200, "text/html", _OFFLINE_PAGE_BODY)


def _get_full_run_answers(
    pdf_answer: SourceHttpResponse,
) -> dict[str, SourceHttpResponse]:
    return {
        _LISTING_URLS[0]: _FIRST_LISTING_ANSWER,
        _LISTING_URLS[1]: _SECOND_LISTING_ANSWER,
        **{
            original_url: pdf_answer
            for original_url, _timestamp in _LATEST_ACT_CAPTURES
        },
    }


class _FakeArchive:
    def __init__(
        self,
        cdx_answer: SourceHttpResponse,
        original_url_to_answer: dict[str, SourceHttpResponse],
    ):
        self.cdx_answer = cdx_answer
        self.original_url_to_answer = original_url_to_answer
        self.cdx_queries: list[tuple[str, str]] = []
        self.capture_requests: list[tuple[str, str]] = []

    @property
    def call_count(self) -> int:
        return len(self.cdx_queries) + len(self.capture_requests)

    def get_cdx(self, url_prefix: str, mime_type: str) -> SourceHttpResponse:
        self.cdx_queries.append((url_prefix, mime_type))
        return self.cdx_answer.model_copy(
            update={"requested_url": url_prefix, "final_url": url_prefix}
        )

    def get_capture(self, timestamp: str, original_url: str) -> SourceHttpResponse:
        self.capture_requests.append((timestamp, original_url))
        capture_url = build_archive_capture_url(timestamp, original_url)
        return self.original_url_to_answer[original_url].model_copy(
            update={"requested_url": capture_url, "final_url": capture_url}
        )

    def get_requested_original_urls(self) -> list[str]:
        return [original_url for _timestamp, original_url in self.capture_requests]


def _get_run_time() -> datetime:
    return _RUN_TIME


def _install_fake_archive(
    monkeypatch: pytest.MonkeyPatch,
    cdx_answer: SourceHttpResponse,
    original_url_to_answer: dict[str, SourceHttpResponse],
) -> _FakeArchive:
    fake_archive = _FakeArchive(cdx_answer, original_url_to_answer)
    monkeypatch.setattr(
        archive_responses_stage, "get_archive_cdx_response", fake_archive.get_cdx
    )
    monkeypatch.setattr(
        archive_responses_stage,
        "get_archive_capture_response",
        fake_archive.get_capture,
    )
    return fake_archive


def test_a_run_stores_the_cdx_answer_the_listing_captures_and_one_pdf_per_code(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_archive = _install_fake_archive(
        monkeypatch, _CDX_ANSWER, _get_full_run_answers(_PDF_ANSWER)
    )

    harvest_run = populate_archive_responses(scratch_session, _get_run_time)

    assert harvest_run.status == HarvestRunStatus.SUCCEEDED
    assert harvest_run.finished_at is not None
    assert harvest_run.requests_sent == _FULL_RUN_REQUEST_COUNT
    assert harvest_run.bodies_stored == _FULL_RUN_REQUEST_COUNT
    assert fake_archive.cdx_queries == [(_ACT_URL_PREFIX, _PDF_MIME_TYPE)]
    assert fake_archive.get_requested_original_urls() == [
        *_LISTING_URLS,
        *[original_url for original_url, _timestamp in _LATEST_ACT_CAPTURES],
    ]
    assert _AA2001_EARLIER_URL not in fake_archive.get_requested_original_urls()
    source_responses = get_source_responses(scratch_session)
    assert len(source_responses) == _FULL_RUN_REQUEST_COUNT
    assert all(
        source_response.source == SourceName.INTERNET_ARCHIVE
        for source_response in source_responses
    )
    assert sorted(source_response.kind for source_response in source_responses) == (
        sorted(
            [
                ResponseKind.CDX_ANSWER,
                *[ResponseKind.LISTING_PAGE] * _LISTING_REQUEST_COUNT,
                *[ResponseKind.DOCUMENT] * len(_LATEST_ACT_CAPTURES),
            ]
        )
    )


def test_a_stored_capture_is_not_fetched_again(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    seed_stored_pdf(
        scratch_session,
        SourceName.INTERNET_ARCHIVE,
        _RUN_TIME - timedelta(days=7),
        build_archive_capture_url("20251231140314", _AA1906_URL),
    )
    fake_archive = _install_fake_archive(
        monkeypatch, _CDX_ANSWER, _get_full_run_answers(_PDF_ANSWER)
    )

    harvest_run = populate_archive_responses(scratch_session, _get_run_time)

    assert harvest_run.status == HarvestRunStatus.SUCCEEDED
    assert _AA1906_URL not in fake_archive.get_requested_original_urls()
    assert fake_archive.get_requested_original_urls() == [
        *_LISTING_URLS,
        *[original_url for original_url, _timestamp in _LATEST_ACT_CAPTURES[1:]],
    ]


def test_a_cdx_answer_that_qualifies_no_capture_fetches_no_pdf(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_archive = _install_fake_archive(
        monkeypatch, _CLTPA_ANSWER, _get_full_run_answers(_PDF_ANSWER)
    )

    harvest_run = populate_archive_responses(scratch_session, _get_run_time)

    assert harvest_run.status == HarvestRunStatus.SUCCEEDED
    assert fake_archive.get_requested_original_urls() == list(_LISTING_URLS)


def test_an_offline_cdx_answer_halts_the_run(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_archive = _install_fake_archive(
        monkeypatch, _OFFLINE_ANSWER, _get_full_run_answers(_PDF_ANSWER)
    )

    harvest_run = populate_archive_responses(scratch_session, _get_run_time)

    assert harvest_run.status == HarvestRunStatus.HALTED
    assert harvest_run.halt_reason == "The CDX answer is not a JSON list of rows"
    assert fake_archive.get_requested_original_urls() == list(_LISTING_URLS)
    stored_kinds = [
        source_response.kind
        for source_response in get_source_responses(scratch_session)
    ]
    assert ResponseKind.CDX_ANSWER in stored_kinds


def test_three_failed_captures_in_a_row_halt_the_run(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_archive = _install_fake_archive(
        monkeypatch, _CDX_ANSWER, _get_full_run_answers(_NOT_FOUND_ANSWER)
    )

    harvest_run = populate_archive_responses(scratch_session, _get_run_time)

    assert harvest_run.status == HarvestRunStatus.HALTED
    assert harvest_run.halt_reason == "3 failures in a row"
    assert harvest_run.failures == _FAILURE_HALT_COUNT
    assert _AA2020_URL not in fake_archive.get_requested_original_urls()


def test_a_gateway_error_counts_as_a_failure(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_archive = _install_fake_archive(
        monkeypatch, _CDX_ANSWER, _get_full_run_answers(_PDF_ANSWER)
    )

    def get_capture(timestamp: str, original_url: str) -> SourceHttpResponse:
        if original_url == _AA2001_LATER_URL:
            raise OpenSgLawGatewayError(
                f"Internet Archive request failed for {original_url}"
            )
        return fake_archive.get_capture(timestamp, original_url)

    monkeypatch.setattr(
        archive_responses_stage, "get_archive_capture_response", get_capture
    )

    harvest_run = populate_archive_responses(scratch_session, _get_run_time)

    assert harvest_run.status == HarvestRunStatus.SUCCEEDED
    assert harvest_run.failures == 1
    assert harvest_run.requests_sent == _FULL_RUN_REQUEST_COUNT - 1


def test_a_running_run_blocks_a_second_one(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    CRUDHarvestRun(scratch_session).create(
        HarvestRun(
            source=SourceName.INTERNET_ARCHIVE,
            status=HarvestRunStatus.RUNNING,
            started_at=_RUN_TIME - timedelta(hours=1),
        )
    )
    fake_archive = _install_fake_archive(
        monkeypatch, _CDX_ANSWER, _get_full_run_answers(_PDF_ANSWER)
    )

    with pytest.raises(OpenSgLawHarvestRunError, match="still RUNNING"):
        populate_archive_responses(scratch_session, _get_run_time)

    assert len(get_harvest_runs(scratch_session)) == 1
    assert fake_archive.call_count == 0


def test_a_run_that_starts_past_the_size_limit_sends_nothing(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    monkeypatch.setattr(
        CRUDDatabaseSize,
        "get_current_database_bytes",
        lambda crud_database_size: _DATABASE_HALT_BYTES + 1,
    )
    fake_archive = _install_fake_archive(
        monkeypatch, _CDX_ANSWER, _get_full_run_answers(_PDF_ANSWER)
    )

    with pytest.raises(OpenSgLawHarvestHaltError, match="past the 10 GB halt"):
        populate_archive_responses(scratch_session, _get_run_time)

    assert get_harvest_runs(scratch_session) == []
    assert fake_archive.call_count == 0


def test_bodies_are_committed_every_hundred(
    scratch_engine: Engine, scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    monkeypatch.setattr(
        archive_responses_stage, "_BODIES_PER_COMMIT", _COMMIT_EVERY_TWO_BODIES
    )
    fake_archive = _install_fake_archive(
        monkeypatch, _CDX_ANSWER, _get_full_run_answers(_PDF_ANSWER)
    )

    def get_cdx(url_prefix: str, mime_type: str) -> SourceHttpResponse:
        raise RuntimeError("the third request broke")

    monkeypatch.setattr(archive_responses_stage, "get_archive_cdx_response", get_cdx)

    with pytest.raises(RuntimeError, match="the third request broke"):
        populate_archive_responses(scratch_session, _get_run_time)

    with Session(scratch_engine) as new_session:
        source_responses = get_source_responses(new_session)
        harvest_runs = get_harvest_runs(new_session)
    assert len(source_responses) == _COMMIT_EVERY_TWO_BODIES
    assert len(harvest_runs) == 1
    assert harvest_runs[0].status == HarvestRunStatus.FAILED
    assert harvest_runs[0].failure_reason == "RuntimeError"
    assert fake_archive.get_requested_original_urls() == list(_LISTING_URLS)


def test_the_listing_capture_asks_for_the_run_time(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_archive = _install_fake_archive(
        monkeypatch, _CDX_ANSWER, _get_full_run_answers(_PDF_ANSWER)
    )

    populate_archive_responses(scratch_session, _get_run_time)

    assert fake_archive.capture_requests[0] == (
        _RUN_TIME.strftime(_CAPTURE_TIMESTAMP_FORMAT),
        _LISTING_URLS[0],
    )
