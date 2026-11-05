from dataclasses import dataclass

import pytest
import requests

from exceptions import OpenSgLawError, OpenSgLawGatewayError
from gateway.elitigation import (
    get_elitigation_judgment_response,
    get_elitigation_listing_response,
)
from gateway.http import (
    CRAWL_USER_AGENT,
    ELITIGATION_PACER,
    INTERNET_ARCHIVE_PACER,
    SSO_PACER,
)
from gateway.internet_archive import (
    get_archive_capture_response,
    get_archive_cdx_response,
)
from gateway.sso import (
    get_sso_document_response,
    get_sso_listing_response,
    get_sso_robots_response,
)
from utils.sso_listing import build_sso_listing_url

_HTTP_OK = 200
_HTTP_SERVER_ERROR = 500
_BODY = b"<html><body>Total Judgment(s) Found : 1</body></html>"
_COURT_FILTER = "SUPCT"
_YEAR = 2024
_PAGE_NUMBER = 2
_LISTING_QUERY = "Filter=SUPCT&YearOfDecision=2024&SortBy=Score&CurrentPage=2"
_JUDGMENT_URL = "https://www.elitigation.sg/gd/s/2024_SGHC_1"
_ELITIGATION_REQUEST_COUNT = 2
_SSO_DOCUMENT_PATH = "/Act/AA2004?ViewType=Pdf&_=20240702194429"
_SSO_LISTING_PAGE_INDEX = 1
_VALIDATED = "validated"
_SENT = "sent"
_ARCHIVE_URL_PREFIX = "sso.agc.gov.sg/Act"
_PDF_MIME_TYPE = "application/pdf"
_ARCHIVE_CAPTURE_TIMESTAMP = "20240716171208"
_ARCHIVE_ORIGINAL_URL = (
    "https://sso.agc.gov.sg/Act/AA1906?ViewType=Pdf&_=20240202184311"
)
_ARCHIVE_CAPTURE_URL = (
    "https://web.archive.org/web/20240716171208id_/"
    "https://sso.agc.gov.sg/Act/AA1906?ViewType=Pdf&_=20240202184311"
)
_ARCHIVE_REQUEST_COUNT = 2
_HTTP_TOO_MANY_REQUESTS = 429
_TOO_MANY_REQUESTS_WAIT_SECONDS = 300
_ARCHIVE_SENDS_BEFORE_FAILING = 4
_ARCHIVE_WAIT_COUNT_BEFORE_FAILING = 7


@dataclass(frozen=True)
class _RecordedRequest:
    url: str
    headers: dict


def _build_response(url: str, status_code: int, body: bytes) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    response.url = url
    response._content = body
    return response


@dataclass(frozen=True)
class _RecordedSsoRequest:
    url: str
    headers: dict
    is_redirect_allowed: object


@pytest.fixture
def recorded_waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    waits: list[float] = []
    monkeypatch.setattr(ELITIGATION_PACER, "sleep", waits.append)
    monkeypatch.setattr(ELITIGATION_PACER, "last_request_ended_at", None)
    return waits


def test_elitigation_gateways_send_the_user_agent_and_are_paced(
    recorded_waits: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded_requests: list[_RecordedRequest] = []

    def fake_get(url: str, headers: dict, **kwargs: object) -> requests.Response:
        recorded_requests.append(_RecordedRequest(url, headers))
        return _build_response(url, _HTTP_OK, _BODY)

    monkeypatch.setattr(requests, "get", fake_get)

    listing_response = get_elitigation_listing_response(
        _COURT_FILTER, _YEAR, _PAGE_NUMBER
    )
    judgment_response = get_elitigation_judgment_response(_JUDGMENT_URL)

    assert len(recorded_requests) == _ELITIGATION_REQUEST_COUNT
    assert all(
        recorded_request.headers == {"User-Agent": CRAWL_USER_AGENT}
        for recorded_request in recorded_requests
    )
    assert recorded_requests[0].url.endswith(f"/gd/Home/Index?{_LISTING_QUERY}")
    assert recorded_requests[1].url == _JUDGMENT_URL
    assert listing_response.body == _BODY
    assert judgment_response.body == _BODY
    assert judgment_response.requested_url == _JUDGMENT_URL
    assert recorded_waits[0] == 0.0
    assert recorded_waits[1] > 0.0


def test_an_elitigation_transport_error_is_a_gateway_error(
    recorded_waits: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_get(url: str, headers: dict, **kwargs: object) -> requests.Response:
        raise requests.exceptions.ConnectionError("connection refused")

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(OpenSgLawGatewayError, match="eLitigation request failed"):
        get_elitigation_judgment_response(_JUDGMENT_URL)


def test_sso_gateways_send_the_user_agent_once_without_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    recorded_requests: list[_RecordedSsoRequest] = []
    monkeypatch.setattr(SSO_PACER, "sleep", lambda seconds: None)

    def fake_get(url: str, headers: dict, **kwargs: object) -> requests.Response:
        events.append(_SENT)
        recorded_requests.append(
            _RecordedSsoRequest(url, headers, kwargs["allow_redirects"])
        )
        return _build_response(url, _HTTP_SERVER_ERROR, b"")

    def validate_can_send() -> None:
        events.append(_VALIDATED)

    monkeypatch.setattr(requests, "get", fake_get)

    robots_response = get_sso_robots_response(validate_can_send)
    listing_response = get_sso_listing_response(
        _SSO_LISTING_PAGE_INDEX, validate_can_send
    )
    document_response = get_sso_document_response(_SSO_DOCUMENT_PATH, validate_can_send)

    assert events == [_VALIDATED, _SENT] * 3
    assert [recorded_request.url for recorded_request in recorded_requests] == [
        "https://sso.agc.gov.sg/robots.txt",
        build_sso_listing_url(_SSO_LISTING_PAGE_INDEX),
        f"https://sso.agc.gov.sg{_SSO_DOCUMENT_PATH}",
    ]
    assert all(
        recorded_request.headers == {"User-Agent": CRAWL_USER_AGENT}
        for recorded_request in recorded_requests
    )
    assert all(
        recorded_request.is_redirect_allowed is False
        for recorded_request in recorded_requests
    )
    assert robots_response.status_code == _HTTP_SERVER_ERROR
    assert listing_response.status_code == _HTTP_SERVER_ERROR
    assert document_response.status_code == _HTTP_SERVER_ERROR


def test_an_sso_request_refused_before_sending_never_reaches_the_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent_urls: list[str] = []
    monkeypatch.setattr(SSO_PACER, "sleep", lambda seconds: None)

    def fake_get(url: str, headers: dict, **kwargs: object) -> requests.Response:
        sent_urls.append(url)
        return _build_response(url, _HTTP_OK, b"")

    def validate_can_send() -> None:
        raise OpenSgLawError("The window is closed")

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(OpenSgLawError, match="window is closed"):
        get_sso_robots_response(validate_can_send)

    assert sent_urls == []


def test_the_sso_listing_urls_are_zero_based_after_the_first_page() -> None:
    assert build_sso_listing_url(0) == (
        "https://sso.agc.gov.sg/Browse/Act/Current/All?PageSize=500"
    )
    assert build_sso_listing_url(1) == (
        "https://sso.agc.gov.sg/Browse/Act/Current/All/1?PageSize=500&SortBy=Title&SortOrder=ASC"
    )


@pytest.fixture
def recorded_archive_waits(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    waits: list[float] = []
    monkeypatch.setattr(INTERNET_ARCHIVE_PACER, "sleep", waits.append)
    monkeypatch.setattr(INTERNET_ARCHIVE_PACER, "last_request_ended_at", None)
    return waits


def test_archive_gateways_send_the_user_agent_and_are_paced(
    recorded_archive_waits: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    recorded_requests: list[_RecordedRequest] = []

    def fake_get(url: str, headers: dict, **kwargs: object) -> requests.Response:
        recorded_requests.append(_RecordedRequest(url, headers))
        return _build_response(url, _HTTP_OK, _BODY)

    monkeypatch.setattr(requests, "get", fake_get)

    cdx_response = get_archive_cdx_response(_ARCHIVE_URL_PREFIX, _PDF_MIME_TYPE)
    capture_response = get_archive_capture_response(
        _ARCHIVE_CAPTURE_TIMESTAMP, _ARCHIVE_ORIGINAL_URL
    )

    assert len(recorded_requests) == _ARCHIVE_REQUEST_COUNT
    assert all(
        recorded_request.headers == {"User-Agent": CRAWL_USER_AGENT}
        for recorded_request in recorded_requests
    )
    assert "matchType=prefix" in recorded_requests[0].url
    assert "filter=mimetype%3Aapplication%2Fpdf" in recorded_requests[0].url
    assert "output=json" in recorded_requests[0].url
    assert recorded_requests[1].url == _ARCHIVE_CAPTURE_URL
    assert cdx_response.body == _BODY
    assert capture_response.requested_url == _ARCHIVE_CAPTURE_URL
    assert recorded_archive_waits[0] == 0.0
    assert recorded_archive_waits[1] > 0.0


def test_an_archive_429_waits_300_seconds_three_times_then_fails(
    recorded_archive_waits: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    send_count = 0

    def fake_get(url: str, headers: dict, **kwargs: object) -> requests.Response:
        nonlocal send_count
        send_count += 1
        return _build_response(url, _HTTP_TOO_MANY_REQUESTS, b"")

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(OpenSgLawGatewayError, match="answered 429 after 3 waits"):
        get_archive_capture_response(_ARCHIVE_CAPTURE_TIMESTAMP, _ARCHIVE_ORIGINAL_URL)

    assert send_count == _ARCHIVE_SENDS_BEFORE_FAILING
    assert len(recorded_archive_waits) == _ARCHIVE_WAIT_COUNT_BEFORE_FAILING
    assert recorded_archive_waits[1::2] == [_TOO_MANY_REQUESTS_WAIT_SECONDS] * 3


def test_an_archive_429_then_200_returns_the_200(
    recorded_archive_waits: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    statuses = [_HTTP_TOO_MANY_REQUESTS, _HTTP_OK]

    def fake_get(url: str, headers: dict, **kwargs: object) -> requests.Response:
        return _build_response(url, statuses.pop(0), _BODY)

    monkeypatch.setattr(requests, "get", fake_get)

    capture_response = get_archive_capture_response(
        _ARCHIVE_CAPTURE_TIMESTAMP, _ARCHIVE_ORIGINAL_URL
    )

    assert capture_response.status_code == _HTTP_OK
    assert statuses == []
    assert _TOO_MANY_REQUESTS_WAIT_SECONDS in recorded_archive_waits
