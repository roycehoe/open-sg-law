from dataclasses import dataclass

import pytest
import requests

from exceptions import OpenSgLawGatewayError
from gateway.elitigation import (
    get_elitigation_judgment_response,
    get_elitigation_listing_response,
)
from gateway.http import CRAWL_USER_AGENT, ELITIGATION_PACER

_HTTP_OK = 200
_BODY = b"<html><body>Total Judgment(s) Found : 1</body></html>"
_COURT_FILTER = "SUPCT"
_YEAR = 2024
_PAGE_NUMBER = 2
_LISTING_QUERY = "Filter=SUPCT&YearOfDecision=2024&SortBy=Score&CurrentPage=2"
_JUDGMENT_URL = "https://www.elitigation.sg/gd/s/2024_SGHC_1"
_ELITIGATION_REQUEST_COUNT = 2


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
