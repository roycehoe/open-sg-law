from functools import partial
from urllib.parse import urlencode

import requests

from exceptions import OpenSgLawGatewayError
from gateway.http import (
    CRAWL_HEADERS,
    INTERNET_ARCHIVE_PACER,
    build_source_http_response,
    send_with_retry,
)
from schemas.source_http_response import SourceHttpResponse
from settings import settings
from utils.archive_capture_url import build_archive_capture_url

_CDX_PATH = "/cdx/search/cdx"
_HTTP_TOO_MANY_REQUESTS = 429
_TOO_MANY_REQUESTS_WAIT_SECONDS = 300
_MAX_TOO_MANY_REQUESTS_WAITS = 3
_REQUEST_TIMEOUT_SECONDS = 60


def _send_archive_request(url: str) -> requests.Response:
    for wait_count in range(_MAX_TOO_MANY_REQUESTS_WAITS + 1):
        response = send_with_retry(
            INTERNET_ARCHIVE_PACER,
            partial(
                requests.get,
                url=url,
                headers=CRAWL_HEADERS,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            ),
            is_too_many_requests_retried=False,
        )
        if response.status_code != _HTTP_TOO_MANY_REQUESTS:
            return response
        if wait_count == _MAX_TOO_MANY_REQUESTS_WAITS:
            break
        INTERNET_ARCHIVE_PACER.sleep(_TOO_MANY_REQUESTS_WAIT_SECONDS)
    raise OpenSgLawGatewayError(
        f"The Internet Archive answered 429 after {_MAX_TOO_MANY_REQUESTS_WAITS} waits"
        f" of {_TOO_MANY_REQUESTS_WAIT_SECONDS} s for {url}"
    )


def _get_response(url: str) -> SourceHttpResponse:
    try:
        return build_source_http_response(url, _send_archive_request(url))
    except requests.exceptions.RequestException as error:
        raise OpenSgLawGatewayError(
            f"Internet Archive request failed for {url}"
        ) from error


def get_archive_cdx_response(url_prefix: str, mime_type: str) -> SourceHttpResponse:
    query = urlencode(
        {
            "url": url_prefix,
            "matchType": "prefix",
            "filter": f"mimetype:{mime_type}",
            "output": "json",
        }
    )
    return _get_response(f"{settings.internet_archive_base_url}{_CDX_PATH}?{query}")


def get_archive_capture_response(
    timestamp: str, original_url: str
) -> SourceHttpResponse:
    return _get_response(build_archive_capture_url(timestamp, original_url))
