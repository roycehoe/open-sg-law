import random
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Optional

import requests

from schemas.source_http_response import SourceHttpResponse

CRAWL_USER_AGENT = "open-sg-law (+https://github.com/roycehoe/open-sg-law/issues)"
CRAWL_HEADERS = {"User-Agent": CRAWL_USER_AGENT}

SSO_GAP_SECONDS = 60.0
INTERNET_ARCHIVE_GAP_SECONDS = 6.0
ELITIGATION_GAP_SECONDS = 2.0

MAX_RETRIES = 4
_BASE_DELAY = 2.0
_BACKOFF_BASE = 2
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_SERVER_ERROR_FLOOR = 500


class CrawlPacer:
    def __init__(
        self,
        gap_seconds: float,
        clock: Callable[[], float],
        sleep: Callable[[float], None],
    ):
        self.gap_seconds = gap_seconds
        self.clock = clock
        self.sleep = sleep
        self.lock = threading.Lock()
        self.last_request_ended_at: Optional[float] = None

    def get_wait_seconds(self) -> float:
        if self.last_request_ended_at is None:
            return 0.0
        return max(0.0, self.gap_seconds - (self.clock() - self.last_request_ended_at))

    def record_request_end(self) -> None:
        self.last_request_ended_at = self.clock()


SSO_PACER = CrawlPacer(SSO_GAP_SECONDS, time.monotonic, time.sleep)
INTERNET_ARCHIVE_PACER = CrawlPacer(
    INTERNET_ARCHIVE_GAP_SECONDS, time.monotonic, time.sleep
)
ELITIGATION_PACER = CrawlPacer(ELITIGATION_GAP_SECONDS, time.monotonic, time.sleep)


@contextmanager
def paced_request(pacer: CrawlPacer) -> Iterator[None]:
    with pacer.lock:
        pacer.sleep(pacer.get_wait_seconds())
        try:
            yield
        finally:
            pacer.record_request_end()


def _is_transient_failure(
    response: requests.Response, is_too_many_requests_retried: bool
) -> bool:
    if response.status_code == _HTTP_TOO_MANY_REQUESTS:
        return is_too_many_requests_retried
    return response.status_code >= _HTTP_SERVER_ERROR_FLOOR


def _get_backoff_seconds(attempt: int) -> float:
    return _BASE_DELAY * (_BACKOFF_BASE**attempt) + random.uniform(0, 1)


def send_with_retry(
    pacer: CrawlPacer,
    send_request: Callable[[], requests.Response],
    is_too_many_requests_retried: bool,
) -> requests.Response:
    for attempt in range(MAX_RETRIES + 1):
        try:
            with paced_request(pacer):
                response = send_request()
        except requests.exceptions.ConnectionError:
            if attempt == MAX_RETRIES:
                raise
            pacer.sleep(_get_backoff_seconds(attempt))
            continue
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES:
                raise
            pacer.sleep(_get_backoff_seconds(attempt))
            continue
        if not _is_transient_failure(response, is_too_many_requests_retried):
            return response
        if attempt == MAX_RETRIES:
            response.raise_for_status()
        pacer.sleep(_get_backoff_seconds(attempt))
    raise requests.exceptions.RetryError(f"No answer after {MAX_RETRIES + 1} sends")


def build_source_http_response(
    requested_url: str, response: requests.Response
) -> SourceHttpResponse:
    return SourceHttpResponse(
        status_code=response.status_code,
        requested_url=requested_url,
        final_url=response.url,
        content_type=response.headers.get("Content-Type"),
        body=response.content,
    )
