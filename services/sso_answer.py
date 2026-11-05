from typing import Optional

from enums import SsoAnswer
from exceptions import OpenSgLawSsoChallengeError
from schemas.source_http_response import SourceHttpResponse

_HTTP_OK = 200
_HTTP_NOT_FOUND = 404
_HTTP_SERVER_ERROR_FLOOR = 500
_PDF_SIGNATURE = b"%PDF-"
_LISTING_CONTENT_TYPE = "text/html"
_LISTING_ROW_MARKER = b'class="non-ajax file-download"'
_ROBOTS_CONTENT_TYPE = "text/plain"


def _has_content_type(content_type: Optional[str], expected_content_type: str) -> bool:
    if content_type is None:
        return False
    return content_type.lower().startswith(expected_content_type)


def is_sso_pdf(source_http_response: SourceHttpResponse) -> bool:
    return source_http_response.body.startswith(_PDF_SIGNATURE)


def is_sso_listing_page(source_http_response: SourceHttpResponse) -> bool:
    if not _has_content_type(source_http_response.content_type, _LISTING_CONTENT_TYPE):
        return False
    return _LISTING_ROW_MARKER in source_http_response.body


def is_sso_robots_file(source_http_response: SourceHttpResponse) -> bool:
    return _has_content_type(source_http_response.content_type, _ROBOTS_CONTENT_TYPE)


def get_sso_answer(
    source_http_response: SourceHttpResponse, is_expected_body: bool
) -> SsoAnswer:
    if source_http_response.status_code == _HTTP_NOT_FOUND:
        return SsoAnswer.FAILURE
    if source_http_response.status_code >= _HTTP_SERVER_ERROR_FLOOR:
        return SsoAnswer.FAILURE
    if source_http_response.status_code == _HTTP_OK and is_expected_body:
        return SsoAnswer.EXPECTED
    raise OpenSgLawSsoChallengeError(
        f"SSO answered {source_http_response.status_code} with {len(source_http_response.body):,} bytes"
        f" of {source_http_response.content_type} to {source_http_response.requested_url}"
    )
