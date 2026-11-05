from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, select

import populate.sso_responses as sso_responses_stage
from crud.database_size import CRUDDatabaseSize
from crud.harvest_run import CRUDHarvestRun
from crud.source import CRUDSource
from crud.source_response import CRUDSourceResponse
from database.harvest_run import HarvestRun
from database.source import Source
from database.source_response import SourceResponse
from enums import HarvestRunStatus, ResponseKind, SourceName, SsoAccessState
from exceptions import (
    OpenSgLawGatewayError,
    OpenSgLawHarvestHaltError,
    OpenSgLawHarvestRunError,
    OpenSgLawSourceStateError,
    OpenSgLawSsoWindowError,
)
from gateway.http import SSO_PACER
from gateway.sso import build_sso_listing_url
from populate.sso_responses import populate_sso_responses
from schemas.source_http_response import SourceHttpResponse
from services.source_response import build_source_response
from services.sso_request import get_act_pdf_paths_to_fetch
from settings import settings
from tests.source_seed import seed_sources
from utils.sso_listing import SsoListingRow

_SINGAPORE = ZoneInfo("Asia/Singapore")
_REQUEST_GAP = timedelta(seconds=60)
_NIGHT_START = datetime(2026, 11, 6, 3, 0, tzinfo=_SINGAPORE)
_BEFORE_WINDOW = datetime(2026, 11, 6, 2, 59, tzinfo=_SINGAPORE)
_NEAR_CUTOFF = datetime(2026, 11, 6, 6, 52, tzinfo=_SINGAPORE)
_CUTOFF = datetime(2026, 11, 6, 6, 55, tzinfo=_SINGAPORE)
_DATABASE_HALT_BYTES = 10 * 1024**3
_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures" / "sso_listing"
_FIRST_LISTING_BODY = (
    _FIXTURES_DIRECTORY / "browse-all-p1-20240716-trimmed.html"
).read_bytes()
_SECOND_LISTING_BODY = (
    _FIXTURES_DIRECTORY / "browse-all-p2-20240719-trimmed.html"
).read_bytes()
_LISTING_CONTENT_TYPE = "text/html; charset=utf-8"
_ROBOTS_CONTENT_TYPE = "text/plain"
_PDF_CONTENT_TYPE = "application/pdf"
_ROBOTS_BODY = b"User-agent: *\nCrawl-delay: 6\nDisallow: /search\n"
_PDF_BODY = b"%PDF-"
_CHALLENGE_BODY = b"<html><body>Access denied</body></html>"
_NOT_FOUND_BODY = b"<html><body>Page not found</body></html>"
_ROBOTS_URL = f"{settings.sso_base_url}/robots.txt"
_LISTED_PDF_PATHS = (
    "/Act/AA2004?ViewType=Pdf&_=20240702194429",
    "/Act/ACRAA2004?ViewType=Pdf&_=20230613004057",
    "/Act/ASA2007?ViewType=Pdf&_=20230401031605",
    "/Act/TCA2005?ViewType=Pdf&_=20240718005803",
    "/Act/TA1967?ViewType=Pdf&_=20231218123028",
    "/Act/UPA1967?ViewType=Pdf&_=20230405134713",
)
_OLDER_ACRAA_PATH = "/Act/ACRAA2004?ViewType=Pdf&_=20200101000000"
_FULL_NIGHT_REQUEST_COUNT = 9
_FAILURE_HALT_COUNT = 3


class _FakeClock:
    def __init__(self, start: datetime):
        self.now = start.astimezone(timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self) -> None:
        self.now += _REQUEST_GAP


def _build_sso_answer(
    status_code: int, content_type: Optional[str], body: bytes
) -> SourceHttpResponse:
    return SourceHttpResponse(
        status_code=status_code,
        requested_url="",
        final_url="",
        content_type=content_type,
        body=body,
    )


_ROBOTS_ANSWER = _build_sso_answer(200, _ROBOTS_CONTENT_TYPE, _ROBOTS_BODY)
_FIRST_LISTING_ANSWER = _build_sso_answer(
    200, _LISTING_CONTENT_TYPE, _FIRST_LISTING_BODY
)
_SECOND_LISTING_ANSWER = _build_sso_answer(
    200, _LISTING_CONTENT_TYPE, _SECOND_LISTING_BODY
)
_PDF_ANSWER = _build_sso_answer(200, _PDF_CONTENT_TYPE, _PDF_BODY)
_FORBIDDEN_ANSWER = _build_sso_answer(403, "text/html", _CHALLENGE_BODY)
_EMPTY_ACCEPTED_ANSWER = _build_sso_answer(202, None, b"")
_NOT_FOUND_ANSWER = _build_sso_answer(404, "text/html", _NOT_FOUND_BODY)


def _get_pdf_url(pdf_path: str) -> str:
    return f"{settings.sso_base_url}{pdf_path}"


class _FakeSso:
    def __init__(
        self,
        fake_clock: _FakeClock,
        url_to_answer: dict[str, SourceHttpResponse],
        failing_urls: frozenset[str],
    ):
        self.fake_clock = fake_clock
        self.url_to_answer = url_to_answer
        self.failing_urls = failing_urls
        self.requested_urls: list[str] = []
        self.sent_at: list[datetime] = []
        self.call_count = 0

    def _answer(
        self, url: str, validate_can_send: Callable[[], None]
    ) -> SourceHttpResponse:
        self.call_count += 1
        self.fake_clock.advance()
        validate_can_send()
        self.requested_urls.append(url)
        self.sent_at.append(self.fake_clock.now)
        if url in self.failing_urls:
            raise OpenSgLawGatewayError(f"SSO request failed for {url}")
        answer = self.url_to_answer[url]
        return answer.model_copy(update={"requested_url": url, "final_url": url})

    def get_robots(self, validate_can_send: Callable[[], None]) -> SourceHttpResponse:
        return self._answer(_ROBOTS_URL, validate_can_send)

    def get_listing(
        self, page_index: int, validate_can_send: Callable[[], None]
    ) -> SourceHttpResponse:
        return self._answer(build_sso_listing_url(page_index), validate_can_send)

    def get_document(
        self, path: str, validate_can_send: Callable[[], None]
    ) -> SourceHttpResponse:
        return self._answer(_get_pdf_url(path), validate_can_send)


def _get_full_night_answers(
    pdf_answer: SourceHttpResponse,
) -> dict[str, SourceHttpResponse]:
    return {
        _ROBOTS_URL: _ROBOTS_ANSWER,
        build_sso_listing_url(0): _FIRST_LISTING_ANSWER,
        build_sso_listing_url(1): _SECOND_LISTING_ANSWER,
        **{_get_pdf_url(pdf_path): pdf_answer for pdf_path in _LISTED_PDF_PATHS},
    }


def _install_fake_sso(
    monkeypatch: pytest.MonkeyPatch,
    fake_clock: _FakeClock,
    url_to_answer: dict[str, SourceHttpResponse],
    failing_urls: frozenset[str] = frozenset(),
) -> _FakeSso:
    fake_sso = _FakeSso(fake_clock, url_to_answer, failing_urls)
    monkeypatch.setattr(SSO_PACER, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        sso_responses_stage, "get_sso_robots_response", fake_sso.get_robots
    )
    monkeypatch.setattr(
        sso_responses_stage, "get_sso_listing_response", fake_sso.get_listing
    )
    monkeypatch.setattr(
        sso_responses_stage, "get_sso_document_response", fake_sso.get_document
    )
    return fake_sso


def _install_database_sizes(
    monkeypatch: pytest.MonkeyPatch, first_bytes: int, later_bytes: int
) -> None:
    database_sizes = [first_bytes]

    def get_current_database_bytes(crud_database_size: CRUDDatabaseSize) -> int:
        if database_sizes:
            return database_sizes.pop()
        return later_bytes

    monkeypatch.setattr(
        CRUDDatabaseSize, "get_current_database_bytes", get_current_database_bytes
    )


def _set_sso_access_state(session: Session, sso_access_state: SsoAccessState) -> None:
    source = CRUDSource(session).get_by_name(SourceName.SSO)
    assert source is not None
    source.sso_access_state = sso_access_state
    CRUDSource(session).update(source)
    session.commit()


def _get_stored_sso_source(engine: Engine) -> Source:
    with Session(engine) as session:
        source = CRUDSource(session).get_by_name(SourceName.SSO)
        assert source is not None
        return source


def _get_harvest_runs(session: Session) -> list[HarvestRun]:
    return list(session.exec(select(HarvestRun)).all())


def _get_source_responses(session: Session) -> list[SourceResponse]:
    return list(session.exec(select(SourceResponse)).all())


def _seed_stored_pdf(session: Session, pdf_path: str) -> None:
    harvest_run = HarvestRun(
        source=SourceName.SSO,
        status=HarvestRunStatus.SUCCEEDED,
        started_at=_NIGHT_START - timedelta(days=7),
    )
    CRUDHarvestRun(session).create(harvest_run)
    assert harvest_run.id is not None
    pdf_url = _get_pdf_url(pdf_path)
    CRUDSourceResponse(session).insert_on_conflict_do_nothing(
        build_source_response(
            _PDF_ANSWER.model_copy(
                update={"requested_url": pdf_url, "final_url": pdf_url}
            ),
            ResponseKind.DOCUMENT,
            SourceName.SSO,
            harvest_run.id,
        )
    )
    session.commit()


def _get_requested_pdf_paths(fake_sso: _FakeSso) -> list[str]:
    return [
        requested_url.removeprefix(settings.sso_base_url)
        for requested_url in fake_sso.requested_urls
        if requested_url.startswith(f"{settings.sso_base_url}/Act/")
    ]


def test_a_run_outside_the_window_sends_nothing(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_clock = _FakeClock(_BEFORE_WINDOW)
    fake_sso = _install_fake_sso(
        monkeypatch, fake_clock, _get_full_night_answers(_PDF_ANSWER)
    )

    with pytest.raises(OpenSgLawSsoWindowError, match="before the 03:00 window"):
        populate_sso_responses(scratch_session, fake_clock)

    assert _get_harvest_runs(scratch_session) == []
    assert fake_sso.call_count == 0


def test_a_challenged_source_sends_nothing(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    _set_sso_access_state(scratch_session, SsoAccessState.CHALLENGED)
    fake_clock = _FakeClock(_NIGHT_START)
    fake_sso = _install_fake_sso(
        monkeypatch, fake_clock, _get_full_night_answers(_PDF_ANSWER)
    )

    with pytest.raises(OpenSgLawSourceStateError, match="SSO is CHALLENGED"):
        populate_sso_responses(scratch_session, fake_clock)

    assert _get_harvest_runs(scratch_session) == []
    assert fake_sso.call_count == 0


def test_a_403_on_the_first_request_writes_challenged_and_halts(
    scratch_engine: Engine, scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_clock = _FakeClock(_NIGHT_START)
    fake_sso = _install_fake_sso(
        monkeypatch, fake_clock, {_ROBOTS_URL: _FORBIDDEN_ANSWER}
    )

    harvest_run = populate_sso_responses(scratch_session, fake_clock)

    stored_source = _get_stored_sso_source(scratch_engine)
    assert stored_source.sso_access_state == SsoAccessState.CHALLENGED
    assert stored_source.sso_access_state_reason is not None
    assert "SSO answered 403" in stored_source.sso_access_state_reason
    assert stored_source.sso_access_state_changed_at == fake_clock.now
    assert harvest_run.status == HarvestRunStatus.HALTED
    assert harvest_run.halt_reason == stored_source.sso_access_state_reason
    source_responses = _get_source_responses(scratch_session)
    assert len(source_responses) == 1
    assert source_responses[0].status_code == _FORBIDDEN_ANSWER.status_code
    assert source_responses[0].body_text == _CHALLENGE_BODY.decode()
    assert fake_sso.requested_urls == [_ROBOTS_URL]


def test_a_202_with_an_empty_body_on_a_pdf_writes_challenged(
    scratch_engine: Engine, scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_clock = _FakeClock(_NIGHT_START)
    fake_sso = _install_fake_sso(
        monkeypatch, fake_clock, _get_full_night_answers(_EMPTY_ACCEPTED_ANSWER)
    )

    harvest_run = populate_sso_responses(scratch_session, fake_clock)

    stored_source = _get_stored_sso_source(scratch_engine)
    assert stored_source.sso_access_state == SsoAccessState.CHALLENGED
    assert stored_source.sso_access_state_reason is not None
    assert "SSO answered 202 with 0 bytes" in stored_source.sso_access_state_reason
    assert harvest_run.status == HarvestRunStatus.HALTED
    assert len(_get_requested_pdf_paths(fake_sso)) == 1


def test_a_403_past_the_size_limit_writes_challenged(
    scratch_engine: Engine, scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    _install_database_sizes(monkeypatch, _DATABASE_HALT_BYTES, _DATABASE_HALT_BYTES + 1)
    fake_clock = _FakeClock(_NIGHT_START)
    fake_sso = _install_fake_sso(
        monkeypatch, fake_clock, {_ROBOTS_URL: _FORBIDDEN_ANSWER}
    )

    harvest_run = populate_sso_responses(scratch_session, fake_clock)

    stored_source = _get_stored_sso_source(scratch_engine)
    assert stored_source.sso_access_state == SsoAccessState.CHALLENGED
    assert stored_source.sso_access_state_reason is not None
    assert "SSO answered 403" in stored_source.sso_access_state_reason
    assert stored_source.sso_access_state_changed_at is not None
    assert harvest_run.status == HarvestRunStatus.HALTED
    assert harvest_run.halt_reason == stored_source.sso_access_state_reason
    assert len(_get_source_responses(scratch_session)) == 1
    assert fake_sso.call_count == 1


def test_a_run_that_starts_past_the_size_limit_sends_nothing(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    _install_database_sizes(
        monkeypatch, _DATABASE_HALT_BYTES + 1, _DATABASE_HALT_BYTES + 1
    )
    fake_clock = _FakeClock(_NIGHT_START)
    fake_sso = _install_fake_sso(
        monkeypatch, fake_clock, _get_full_night_answers(_PDF_ANSWER)
    )

    with pytest.raises(OpenSgLawHarvestHaltError, match="past the 10 GB halt"):
        populate_sso_responses(scratch_session, fake_clock)

    assert _get_harvest_runs(scratch_session) == []
    assert fake_sso.call_count == 0


def test_an_expected_answer_past_the_size_limit_halts_before_the_next_request(
    scratch_engine: Engine, scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    _install_database_sizes(monkeypatch, _DATABASE_HALT_BYTES, _DATABASE_HALT_BYTES + 1)
    fake_clock = _FakeClock(_NIGHT_START)
    fake_sso = _install_fake_sso(
        monkeypatch, fake_clock, _get_full_night_answers(_PDF_ANSWER)
    )

    harvest_run = populate_sso_responses(scratch_session, fake_clock)

    assert _get_stored_sso_source(scratch_engine).sso_access_state == (
        SsoAccessState.SERVING
    )
    assert harvest_run.status == HarvestRunStatus.HALTED
    assert harvest_run.halt_reason is not None
    assert "past the 10 GB halt" in harvest_run.halt_reason
    assert fake_sso.requested_urls == [_ROBOTS_URL]


def test_a_night_stores_robots_the_listing_and_the_new_pdfs(
    scratch_engine: Engine, scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_clock = _FakeClock(_NIGHT_START)
    fake_sso = _install_fake_sso(
        monkeypatch, fake_clock, _get_full_night_answers(_PDF_ANSWER)
    )

    harvest_run = populate_sso_responses(scratch_session, fake_clock)

    stored_source = _get_stored_sso_source(scratch_engine)
    assert stored_source.sso_access_state == SsoAccessState.SERVING
    assert stored_source.sso_access_state_reason == "First expected answer"
    assert harvest_run.status == HarvestRunStatus.SUCCEEDED
    assert harvest_run.finished_at is not None
    assert fake_sso.call_count == _FULL_NIGHT_REQUEST_COUNT
    assert harvest_run.requests_sent == _FULL_NIGHT_REQUEST_COUNT
    assert harvest_run.bodies_stored == _FULL_NIGHT_REQUEST_COUNT
    assert sorted(_get_requested_pdf_paths(fake_sso)) == sorted(_LISTED_PDF_PATHS)
    assert len(_get_source_responses(scratch_session)) == _FULL_NIGHT_REQUEST_COUNT


def test_a_pdf_whose_stamp_is_stored_is_not_requested_and_new_codes_come_first(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    _seed_stored_pdf(scratch_session, _LISTED_PDF_PATHS[0])
    _seed_stored_pdf(scratch_session, _OLDER_ACRAA_PATH)
    fake_clock = _FakeClock(_NIGHT_START)
    fake_sso = _install_fake_sso(
        monkeypatch, fake_clock, _get_full_night_answers(_PDF_ANSWER)
    )

    harvest_run = populate_sso_responses(scratch_session, fake_clock)

    assert harvest_run.status == HarvestRunStatus.SUCCEEDED
    assert _get_requested_pdf_paths(fake_sso) == [
        "/Act/ASA2007?ViewType=Pdf&_=20230401031605",
        "/Act/TA1967?ViewType=Pdf&_=20231218123028",
        "/Act/TCA2005?ViewType=Pdf&_=20240718005803",
        "/Act/UPA1967?ViewType=Pdf&_=20230405134713",
        "/Act/ACRAA2004?ViewType=Pdf&_=20230613004057",
    ]


def test_the_cutoff_ends_the_night_as_succeeded(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_clock = _FakeClock(_NEAR_CUTOFF)
    fake_sso = _install_fake_sso(
        monkeypatch, fake_clock, _get_full_night_answers(_PDF_ANSWER)
    )

    harvest_run = populate_sso_responses(scratch_session, fake_clock)

    assert harvest_run.status == HarvestRunStatus.SUCCEEDED
    assert fake_sso.requested_urls == [_ROBOTS_URL, build_sso_listing_url(0)]
    assert all(sent_at < _CUTOFF for sent_at in fake_sso.sent_at)
    assert harvest_run.requests_sent == len(fake_sso.requested_urls)


def test_three_failures_in_a_row_halt_the_run(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_clock = _FakeClock(_NIGHT_START)
    fake_sso = _install_fake_sso(
        monkeypatch, fake_clock, _get_full_night_answers(_NOT_FOUND_ANSWER)
    )

    harvest_run = populate_sso_responses(scratch_session, fake_clock)

    assert harvest_run.status == HarvestRunStatus.HALTED
    assert harvest_run.halt_reason == "3 failures in a row"
    assert harvest_run.failures == _FAILURE_HALT_COUNT
    assert len(_get_requested_pdf_paths(fake_sso)) == _FAILURE_HALT_COUNT


def test_a_gateway_error_counts_as_a_failure(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    fake_clock = _FakeClock(_NIGHT_START)
    fake_sso = _install_fake_sso(
        monkeypatch,
        fake_clock,
        _get_full_night_answers(_PDF_ANSWER),
        frozenset({_ROBOTS_URL}),
    )

    harvest_run = populate_sso_responses(scratch_session, fake_clock)

    assert harvest_run.status == HarvestRunStatus.SUCCEEDED
    assert harvest_run.failures == 1
    assert harvest_run.requests_sent == _FULL_NIGHT_REQUEST_COUNT - 1
    assert fake_sso.call_count == _FULL_NIGHT_REQUEST_COUNT


def test_a_running_run_blocks_a_second_one(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    CRUDHarvestRun(scratch_session).create(
        HarvestRun(
            source=SourceName.SSO,
            status=HarvestRunStatus.RUNNING,
            started_at=_NIGHT_START - timedelta(hours=1),
        )
    )
    fake_clock = _FakeClock(_NIGHT_START)
    fake_sso = _install_fake_sso(
        monkeypatch, fake_clock, _get_full_night_answers(_PDF_ANSWER)
    )

    with pytest.raises(OpenSgLawHarvestRunError, match="still RUNNING"):
        populate_sso_responses(scratch_session, fake_clock)

    assert len(_get_harvest_runs(scratch_session)) == 1
    assert fake_sso.call_count == 0


def test_get_act_pdf_paths_to_fetch_orders_and_skips() -> None:
    listing_rows = [
        SsoListingRow(
            "AA2004", "Accountants Act 2004", _LISTED_PDF_PATHS[0], "20240702194429"
        ),
        SsoListingRow("ZZ1999", "Unstamped Act 1999", "/Act/ZZ1999?ViewType=Pdf", None),
        SsoListingRow(
            "BB2001",
            "Older Act 2001",
            "/Act/BB2001?ViewType=Pdf&_=20240101000000",
            "20240101000000",
        ),
        SsoListingRow(
            "CC2002",
            "Oldest Act 2002",
            "/Act/CC2002?ViewType=Pdf&_=20240101000000",
            "20240101000000",
        ),
    ]
    stored_document_urls = [
        _get_pdf_url(_LISTED_PDF_PATHS[0]),
        _get_pdf_url("/Act/BB2001?ViewType=Pdf&_=20230101000000"),
        f"https://web.archive.org/web/20240716171208id_/{_get_pdf_url('/Act/CC2002?ViewType=Pdf&_=20220101000000')}",
        _get_pdf_url("/Act/CC2002/Historical/20200101?ViewType=Pdf&_=20230601000000"),
    ]

    assert get_act_pdf_paths_to_fetch(listing_rows, stored_document_urls) == [
        "/Act/ZZ1999?ViewType=Pdf",
        "/Act/CC2002?ViewType=Pdf&_=20240101000000",
        "/Act/BB2001?ViewType=Pdf&_=20240101000000",
    ]
