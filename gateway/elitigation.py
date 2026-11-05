from functools import partial
from urllib.parse import urlencode

import requests

from exceptions import OpenSgLawGatewayError
from gateway.http import (
    CRAWL_HEADERS,
    ELITIGATION_PACER,
    build_source_http_response,
    send_with_retry,
)
from schemas.source_http_response import SourceHttpResponse
from settings import settings

_LISTING_PATH = "/gd/Home/Index"
_LISTING_SORT_BY = "Score"
_REQUEST_TIMEOUT_SECONDS = 60


def _get_response(url: str) -> SourceHttpResponse:
    try:
        response = send_with_retry(
            ELITIGATION_PACER,
            partial(
                requests.get,
                url=url,
                headers=CRAWL_HEADERS,
                timeout=_REQUEST_TIMEOUT_SECONDS,
            ),
            is_too_many_requests_retried=True,
        )
        return build_source_http_response(url, response)
    except requests.exceptions.RequestException as error:
        raise OpenSgLawGatewayError(f"eLitigation request failed for {url}") from error


def get_elitigation_listing_response(
    court_filter: str, year: int, page_number: int
) -> SourceHttpResponse:
    query = urlencode(
        {
            "Filter": court_filter,
            "YearOfDecision": year,
            "SortBy": _LISTING_SORT_BY,
            "CurrentPage": page_number,
        }
    )
    return _get_response(f"{settings.elitigation_base_url}{_LISTING_PATH}?{query}")


def get_elitigation_judgment_response(url: str) -> SourceHttpResponse:
    return _get_response(url)
