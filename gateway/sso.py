from collections.abc import Callable

import requests

from exceptions import OpenSgLawGatewayError
from gateway.http import (
    CRAWL_HEADERS,
    SSO_PACER,
    build_source_http_response,
    paced_request,
)
from schemas.source_http_response import SourceHttpResponse
from settings import settings
from utils.sso_listing import build_sso_listing_url

_ROBOTS_PATH = "/robots.txt"
_REQUEST_TIMEOUT_SECONDS = 60


def _get_response(
    url: str, validate_can_send: Callable[[], None]
) -> SourceHttpResponse:
    try:
        with paced_request(SSO_PACER):
            validate_can_send()
            response = requests.get(
                url,
                headers=CRAWL_HEADERS,
                timeout=_REQUEST_TIMEOUT_SECONDS,
                allow_redirects=False,
            )
        return build_source_http_response(url, response)
    except requests.exceptions.RequestException as error:
        raise OpenSgLawGatewayError(f"SSO request failed for {url}") from error


def get_sso_robots_response(
    validate_can_send: Callable[[], None],
) -> SourceHttpResponse:
    return _get_response(f"{settings.sso_base_url}{_ROBOTS_PATH}", validate_can_send)


def get_sso_listing_response(
    page_index: int, validate_can_send: Callable[[], None]
) -> SourceHttpResponse:
    return _get_response(build_sso_listing_url(page_index), validate_can_send)


def get_sso_document_response(
    path: str, validate_can_send: Callable[[], None]
) -> SourceHttpResponse:
    return _get_response(f"{settings.sso_base_url}{path}", validate_can_send)
