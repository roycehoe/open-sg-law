from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

import populate.elitigation_responses as elitigation_responses_stage
from crud.database_size import CRUDDatabaseSize
from crud.harvest_run import CRUDHarvestRun
from crud.source_response import CRUDSourceResponse
from database.harvest_run import HarvestRun
from enums import HarvestRunStatus, ResponseKind, SourceName
from exceptions import (
    OpenSgLawGatewayError,
    OpenSgLawHarvestHaltError,
    OpenSgLawHarvestRunError,
)
from populate.elitigation_responses import populate_elitigation_responses
from schemas.source_http_response import SourceHttpResponse
from services.source_response import build_source_response
from tests.source_seed import (
    build_source_http_answer,
    get_harvest_runs,
    get_source_responses,
    seed_sources,
)

_RUN_TIME = datetime(2025, 12, 31, 19, 0, tzinfo=timezone.utc)
_RUN_YEAR = 2025
_DATABASE_HALT_BYTES = 10 * 1_024**3
_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures" / "elitigation"
_HTML_CONTENT_TYPE = "text/html; charset=utf-8"
_YEAR_PAGE_COUNT = 58
_YEAR_TOTAL = 573
_FIRST_PAGE_URL_COUNT = 10
_LAST_PAGE_URL_COUNT = 3
_JUDGMENT_URL_COUNT = _FIRST_PAGE_URL_COUNT + _LAST_PAGE_URL_COUNT
_FULL_RUN_REQUEST_COUNT = _YEAR_PAGE_COUNT + _JUDGMENT_URL_COUNT
_FAILURE_HALT_COUNT = 3
_COMMIT_EVERY_TWO_BODIES = 2
_JUDGMENT_BASE_URL = "https://www.elitigation.sg/gd/s/"
_FIRST_JUDGMENT_URL = f"{_JUDGMENT_BASE_URL}2025_SGHC_267"
_LAST_JUDGMENT_URL = f"{_JUDGMENT_BASE_URL}2025_SGCA_1"
_FIRST_PAGE_BODY = (_FIXTURES_DIRECTORY / "supct-2025-page-1.html").read_bytes()
_LAST_PAGE_BODY = (_FIXTURES_DIRECTORY / "supct-2025-page-58.html").read_bytes()
_SYSTEM_ERROR_BODY = (
    _FIXTURES_DIRECTORY / "statect-2025-system-error.html"
).read_bytes()
_JUDGMENT_BODY = (_FIXTURES_DIRECTORY / "made-up-high-court-judgment.html").read_bytes()
_FIRST_PAGE_ANSWER = build_source_http_answer(200, _HTML_CONTENT_TYPE, _FIRST_PAGE_BODY)
_LAST_PAGE_ANSWER = build_source_http_answer(200, _HTML_CONTENT_TYPE, _LAST_PAGE_BODY)
_SYSTEM_ERROR_ANSWER = build_source_http_answer(
    200, _HTML_CONTENT_TYPE, _SYSTEM_ERROR_BODY
)
_JUDGMENT_ANSWER = build_source_http_answer(200, _HTML_CONTENT_TYPE, _JUDGMENT_BODY)
_NOT_FOUND_ANSWER = build_source_http_answer(404, "text/html", b"<html></html>")


class _LogRecorder:
    def __init__(self):
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)

    def warning(self, message: str) -> None:
        self.messages.append(message)


class _FakeElitigation:
    def __init__(
        self,
        first_page_answer: SourceHttpResponse,
        judgment_answer: SourceHttpResponse,
    ):
        self.first_page_answer = first_page_answer
        self.judgment_answer = judgment_answer
        self.listing_requests: list[tuple[str, int, int]] = []
        self.judgment_requests: list[str] = []

    @property
    def call_count(self) -> int:
        return len(self.listing_requests) + len(self.judgment_requests)

    def get_listing(
        self, court_filter: str, year: int, page_number: int
    ) -> SourceHttpResponse:
        self.listing_requests.append((court_filter, year, page_number))
        listing_url = f"listing:{court_filter}:{year}:{page_number}"
        listing_answer = (
            self.first_page_answer if page_number == 1 else _LAST_PAGE_ANSWER
        )
        return listing_answer.model_copy(
            update={"requested_url": listing_url, "final_url": listing_url}
        )

    def get_judgment(self, url: str) -> SourceHttpResponse:
        self.judgment_requests.append(url)
        return self.judgment_answer.model_copy(
            update={"requested_url": url, "final_url": url}
        )


def _get_run_time() -> datetime:
    return _RUN_TIME


def _install_fake_elitigation(
    monkeypatch: pytest.MonkeyPatch,
    first_page_answer: SourceHttpResponse = _FIRST_PAGE_ANSWER,
    judgment_answer: SourceHttpResponse = _JUDGMENT_ANSWER,
) -> _FakeElitigation:
    fake_elitigation = _FakeElitigation(first_page_answer, judgment_answer)
    monkeypatch.setattr(elitigation_responses_stage, "_FIRST_YEAR", _RUN_YEAR)
    monkeypatch.setattr(
        elitigation_responses_stage,
        "get_elitigation_listing_response",
        fake_elitigation.get_listing,
    )
    monkeypatch.setattr(
        elitigation_responses_stage,
        "get_elitigation_judgment_response",
        fake_elitigation.get_judgment,
    )
    return fake_elitigation


def _seed_stored_judgment(
    session: Session, judgment_url: str, judgment_answer: SourceHttpResponse
) -> None:
    harvest_run = HarvestRun(
        source=SourceName.ELITIGATION,
        status=HarvestRunStatus.SUCCEEDED,
        started_at=_RUN_TIME - timedelta(days=7),
    )
    CRUDHarvestRun(session).create(harvest_run)
    assert harvest_run.id is not None
    CRUDSourceResponse(session).insert_on_conflict_do_nothing(
        build_source_response(
            judgment_answer.model_copy(
                update={"requested_url": judgment_url, "final_url": judgment_url}
            ),
            ResponseKind.DOCUMENT,
            SourceName.ELITIGATION,
            harvest_run.id,
        )
    )
    session.commit()


def test_a_run_stores_every_listing_page_then_every_listed_judgment(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    log_recorder = _LogRecorder()
    monkeypatch.setattr(elitigation_responses_stage, "logger", log_recorder)
    fake_elitigation = _install_fake_elitigation(monkeypatch)

    harvest_run = populate_elitigation_responses(scratch_session, _get_run_time)

    assert harvest_run.status == HarvestRunStatus.SUCCEEDED
    assert harvest_run.finished_at is not None
    assert harvest_run.requests_sent == _FULL_RUN_REQUEST_COUNT
    assert harvest_run.bodies_stored == _FULL_RUN_REQUEST_COUNT
    assert fake_elitigation.listing_requests == [
        ("SUPCT", _RUN_YEAR, page_number)
        for page_number in range(1, _YEAR_PAGE_COUNT + 1)
    ]
    assert len(fake_elitigation.judgment_requests) == _JUDGMENT_URL_COUNT
    assert fake_elitigation.judgment_requests[0] == _FIRST_JUDGMENT_URL
    assert fake_elitigation.judgment_requests[-1] == _LAST_JUDGMENT_URL
    source_responses = get_source_responses(scratch_session)
    assert all(
        source_response.source == SourceName.ELITIGATION
        for source_response in source_responses
    )
    assert (
        len(
            [
                source_response
                for source_response in source_responses
                if source_response.kind == ResponseKind.LISTING_PAGE
            ]
        )
        == _YEAR_PAGE_COUNT
    )
    assert (
        f"{_RUN_YEAR}: {_JUDGMENT_URL_COUNT} of {_YEAR_TOTAL} judgments stored"
        in log_recorder.messages
    )


def test_a_stored_judgment_with_a_citation_is_not_fetched_again(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    _seed_stored_judgment(scratch_session, _FIRST_JUDGMENT_URL, _JUDGMENT_ANSWER)
    fake_elitigation = _install_fake_elitigation(monkeypatch)

    harvest_run = populate_elitigation_responses(scratch_session, _get_run_time)

    assert harvest_run.status == HarvestRunStatus.SUCCEEDED
    assert _FIRST_JUDGMENT_URL not in fake_elitigation.judgment_requests
    assert len(fake_elitigation.judgment_requests) == _JUDGMENT_URL_COUNT - 1


def test_a_stored_judgment_without_a_citation_is_fetched_again(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    _seed_stored_judgment(scratch_session, _FIRST_JUDGMENT_URL, _SYSTEM_ERROR_ANSWER)
    fake_elitigation = _install_fake_elitigation(monkeypatch)

    populate_elitigation_responses(scratch_session, _get_run_time)

    assert _FIRST_JUDGMENT_URL in fake_elitigation.judgment_requests


def test_three_judgments_without_a_citation_are_stored_and_halt_the_run(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_elitigation = _install_fake_elitigation(
        monkeypatch, judgment_answer=_SYSTEM_ERROR_ANSWER
    )

    harvest_run = populate_elitigation_responses(scratch_session, _get_run_time)

    assert harvest_run.status == HarvestRunStatus.HALTED
    assert harvest_run.halt_reason == "3 failures in a row"
    assert harvest_run.failures == _FAILURE_HALT_COUNT
    assert len(fake_elitigation.judgment_requests) == _FAILURE_HALT_COUNT
    stored_documents = [
        source_response
        for source_response in get_source_responses(scratch_session)
        if source_response.kind == ResponseKind.DOCUMENT
    ]
    assert len(stored_documents) == _FAILURE_HALT_COUNT


def test_a_judgment_answered_with_a_status_other_than_200_is_a_failure(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    _install_fake_elitigation(monkeypatch, judgment_answer=_NOT_FOUND_ANSWER)

    harvest_run = populate_elitigation_responses(scratch_session, _get_run_time)

    assert harvest_run.status == HarvestRunStatus.HALTED
    assert harvest_run.failures == _FAILURE_HALT_COUNT


def test_a_first_page_with_no_total_halts_the_run(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_elitigation = _install_fake_elitigation(
        monkeypatch, first_page_answer=_SYSTEM_ERROR_ANSWER
    )

    harvest_run = populate_elitigation_responses(scratch_session, _get_run_time)

    assert harvest_run.status == HarvestRunStatus.HALTED
    assert harvest_run.halt_reason == f"{_RUN_YEAR}: the first listing page was not read"
    assert harvest_run.failures == 1
    assert harvest_run.requests_sent == 1
    assert fake_elitigation.call_count == 1
    stored_responses = get_source_responses(scratch_session)
    assert [source_response.kind for source_response in stored_responses] == [
        ResponseKind.LISTING_PAGE
    ]


def test_a_stored_invalid_citation_is_fetched_again(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    invalid_answer = _JUDGMENT_ANSWER.model_copy(
        update={"body": b"<html><title>[not a citation]</title></html>"}
    )
    _seed_stored_judgment(scratch_session, _FIRST_JUDGMENT_URL, invalid_answer)
    fake_elitigation = _install_fake_elitigation(monkeypatch)

    populate_elitigation_responses(scratch_session, _get_run_time)

    assert _FIRST_JUDGMENT_URL in fake_elitigation.judgment_requests


def test_a_gateway_error_counts_as_a_failure(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_elitigation = _install_fake_elitigation(monkeypatch)

    def get_judgment(url: str) -> SourceHttpResponse:
        if url == _FIRST_JUDGMENT_URL:
            raise OpenSgLawGatewayError(f"eLitigation request failed for {url}")
        return fake_elitigation.get_judgment(url)

    monkeypatch.setattr(
        elitigation_responses_stage, "get_elitigation_judgment_response", get_judgment
    )

    harvest_run = populate_elitigation_responses(scratch_session, _get_run_time)

    assert harvest_run.status == HarvestRunStatus.SUCCEEDED
    assert harvest_run.failures == 1
    assert harvest_run.requests_sent == _FULL_RUN_REQUEST_COUNT - 1


def test_a_running_run_blocks_a_second_one(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    CRUDHarvestRun(scratch_session).create(
        HarvestRun(
            source=SourceName.ELITIGATION,
            status=HarvestRunStatus.RUNNING,
            started_at=_RUN_TIME - timedelta(hours=1),
        )
    )
    fake_elitigation = _install_fake_elitigation(monkeypatch)

    with pytest.raises(OpenSgLawHarvestRunError, match="still RUNNING"):
        populate_elitigation_responses(scratch_session, _get_run_time)

    assert len(get_harvest_runs(scratch_session)) == 1
    assert fake_elitigation.call_count == 0


def test_a_run_that_starts_past_the_size_limit_sends_nothing(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    monkeypatch.setattr(
        CRUDDatabaseSize,
        "get_current_database_bytes",
        lambda crud_database_size: _DATABASE_HALT_BYTES + 1,
    )
    fake_elitigation = _install_fake_elitigation(monkeypatch)

    with pytest.raises(OpenSgLawHarvestHaltError, match="past the 10 GB halt"):
        populate_elitigation_responses(scratch_session, _get_run_time)

    assert get_harvest_runs(scratch_session) == []
    assert fake_elitigation.call_count == 0


def test_bodies_are_committed_every_hundred(
    scratch_engine: Engine, scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    monkeypatch.setattr(
        elitigation_responses_stage, "_BODIES_PER_COMMIT", _COMMIT_EVERY_TWO_BODIES
    )
    fake_elitigation = _install_fake_elitigation(monkeypatch)

    def get_listing(
        court_filter: str, year: int, page_number: int
    ) -> SourceHttpResponse:
        if page_number == _COMMIT_EVERY_TWO_BODIES + 1:
            raise RuntimeError("the third request broke")
        return fake_elitigation.get_listing(court_filter, year, page_number)

    monkeypatch.setattr(
        elitigation_responses_stage, "get_elitigation_listing_response", get_listing
    )

    with pytest.raises(RuntimeError, match="the third request broke"):
        populate_elitigation_responses(scratch_session, _get_run_time)

    with Session(scratch_engine) as new_session:
        source_responses = get_source_responses(new_session)
        harvest_runs = get_harvest_runs(new_session)
    assert len(source_responses) == _COMMIT_EVERY_TWO_BODIES
    assert len(harvest_runs) == 1
    assert harvest_runs[0].status == HarvestRunStatus.FAILED
    assert harvest_runs[0].failure_reason == "RuntimeError"
