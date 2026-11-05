from collections.abc import Callable
from dataclasses import dataclass

import pytest
import requests

import gateway.http
from gateway.http import (
    CRAWL_USER_AGENT,
    ELITIGATION_GAP_SECONDS,
    INTERNET_ARCHIVE_GAP_SECONDS,
    MAX_RETRIES,
    SSO_GAP_SECONDS,
    CrawlPacer,
    paced_request,
    send_with_retry,
)

_GAP_SECONDS = 6.0
_PROMISED_SSO_GAP_SECONDS = 60.0
_PROMISED_INTERNET_ARCHIVE_GAP_SECONDS = 6.0
_PROMISED_ELITIGATION_GAP_SECONDS = 2.0
_REQUEST_SECONDS = 0.25
_IDLE_SECONDS = 2.0
_HTTP_OK = 200
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_SERVICE_UNAVAILABLE = 503
_RETRIED_SEND_COUNT = 2
_PACED_SEND_COUNT = 3
_EXPECTED_USER_AGENT = "open-sg-law (+https://github.com/roycehoe/open-sg-law/issues)"


@dataclass
class _RecordedSend:
    started_at: float
    ended_at: float


class _FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def get_time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _build_pacer(fake_clock: _FakeClock) -> CrawlPacer:
    return CrawlPacer(_GAP_SECONDS, fake_clock.get_time, fake_clock.sleep)


def _build_response(status_code: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status_code
    return response


def _get_zero_jitter(low: float, high: float) -> float:
    return 0.0


def _get_sender(
    fake_clock: _FakeClock,
    recorded_sends: list[_RecordedSend],
    responses: list[requests.Response],
) -> Callable[[], requests.Response]:
    def send_request() -> requests.Response:
        started_at = fake_clock.now
        fake_clock.now += _REQUEST_SECONDS
        recorded_sends.append(_RecordedSend(started_at, fake_clock.now))
        if len(responses) > 1:
            return responses.pop(0)
        return responses[0]

    return send_request


def _assert_paced(recorded_sends: list[_RecordedSend]) -> None:
    for previous, current in zip(recorded_sends, recorded_sends[1:]):
        assert current.started_at - previous.ended_at >= _GAP_SECONDS


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> _FakeClock:
    monkeypatch.setattr(gateway.http.random, "uniform", _get_zero_jitter)
    return _FakeClock()


def test_requests_through_one_pacer_are_spaced_by_its_gap(
    fake_clock: _FakeClock,
) -> None:
    pacer = _build_pacer(fake_clock)

    for _ in range(_PACED_SEND_COUNT):
        with paced_request(pacer):
            fake_clock.now += _REQUEST_SECONDS
        fake_clock.now += _IDLE_SECONDS

    assert fake_clock.sleeps == [
        0.0,
        _GAP_SECONDS - _IDLE_SECONDS,
        _GAP_SECONDS - _IDLE_SECONDS,
    ]


def test_pacers_for_two_hosts_do_not_wait_for_each_other(
    fake_clock: _FakeClock,
) -> None:
    first_pacer = _build_pacer(fake_clock)
    second_pacer = _build_pacer(fake_clock)

    with paced_request(first_pacer):
        fake_clock.now += _REQUEST_SECONDS
    with paced_request(second_pacer):
        fake_clock.now += _REQUEST_SECONDS

    assert fake_clock.sleeps == [0.0, 0.0]


def test_a_failed_send_still_counts_toward_the_gap(fake_clock: _FakeClock) -> None:
    pacer = _build_pacer(fake_clock)

    with pytest.raises(ValueError):
        with paced_request(pacer):
            fake_clock.now += _REQUEST_SECONDS
            raise ValueError("request failed")

    assert pacer.last_request_ended_at == _REQUEST_SECONDS
    with paced_request(pacer):
        pass
    assert fake_clock.sleeps == [0.0, _GAP_SECONDS]


def test_a_server_error_is_retried_through_the_pacer(fake_clock: _FakeClock) -> None:
    pacer = _build_pacer(fake_clock)
    recorded_sends: list[_RecordedSend] = []
    server_error_response = _build_response(_HTTP_SERVICE_UNAVAILABLE)
    ok_response = _build_response(_HTTP_OK)
    send_request = _get_sender(
        fake_clock,
        recorded_sends,
        [server_error_response] * _RETRIED_SEND_COUNT + [ok_response],
    )

    assert send_with_retry(pacer, send_request, False) is ok_response
    assert len(recorded_sends) == _RETRIED_SEND_COUNT + 1
    _assert_paced(recorded_sends)


def test_a_server_error_raises_after_the_last_send(fake_clock: _FakeClock) -> None:
    pacer = _build_pacer(fake_clock)
    recorded_sends: list[_RecordedSend] = []
    send_request = _get_sender(
        fake_clock, recorded_sends, [_build_response(_HTTP_SERVICE_UNAVAILABLE)]
    )

    with pytest.raises(requests.exceptions.HTTPError):
        send_with_retry(pacer, send_request, False)

    assert len(recorded_sends) == MAX_RETRIES + 1
    _assert_paced(recorded_sends)


def test_a_too_many_requests_answer_is_retried_when_asked(
    fake_clock: _FakeClock,
) -> None:
    pacer = _build_pacer(fake_clock)
    recorded_sends: list[_RecordedSend] = []
    too_many_requests_response = _build_response(_HTTP_TOO_MANY_REQUESTS)
    ok_response = _build_response(_HTTP_OK)
    send_request = _get_sender(
        fake_clock,
        recorded_sends,
        [too_many_requests_response] * _RETRIED_SEND_COUNT + [ok_response],
    )

    assert send_with_retry(pacer, send_request, True) is ok_response
    assert len(recorded_sends) == _RETRIED_SEND_COUNT + 1
    _assert_paced(recorded_sends)


def test_a_too_many_requests_answer_is_returned_when_not_retried(
    fake_clock: _FakeClock,
) -> None:
    pacer = _build_pacer(fake_clock)
    recorded_sends: list[_RecordedSend] = []
    too_many_requests_response = _build_response(_HTTP_TOO_MANY_REQUESTS)
    send_request = _get_sender(fake_clock, recorded_sends, [too_many_requests_response])

    assert send_with_retry(pacer, send_request, False) is too_many_requests_response
    assert len(recorded_sends) == 1


def test_a_connection_error_is_retried_then_raised(fake_clock: _FakeClock) -> None:
    pacer = _build_pacer(fake_clock)
    recorded_sends: list[_RecordedSend] = []

    def send_request() -> requests.Response:
        started_at = fake_clock.now
        fake_clock.now += _REQUEST_SECONDS
        recorded_sends.append(_RecordedSend(started_at, fake_clock.now))
        raise requests.exceptions.ConnectionError("connection refused")

    with pytest.raises(requests.exceptions.ConnectionError):
        send_with_retry(pacer, send_request, False)

    assert len(recorded_sends) == MAX_RETRIES + 1
    _assert_paced(recorded_sends)


def test_the_gaps_are_the_ones_the_letters_promise() -> None:
    assert SSO_GAP_SECONDS == _PROMISED_SSO_GAP_SECONDS
    assert INTERNET_ARCHIVE_GAP_SECONDS == _PROMISED_INTERNET_ARCHIVE_GAP_SECONDS
    assert ELITIGATION_GAP_SECONDS == _PROMISED_ELITIGATION_GAP_SECONDS


def test_the_user_agent_names_the_project_and_its_issues_page() -> None:
    assert CRAWL_USER_AGENT == _EXPECTED_USER_AGENT
    assert "@" not in CRAWL_USER_AGENT
