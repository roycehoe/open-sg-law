from typing import Optional

import pytest

from enums import SsoAnswer
from exceptions import OpenSgLawSsoChallengeError
from schemas.source_http_response import SourceHttpResponse
from services.sso_answer import (
    get_sso_answer,
    is_sso_listing_page,
    is_sso_pdf,
    is_sso_robots_file,
)

_PDF_URL = "https://sso.agc.gov.sg/Act/AA2004?ViewType=Pdf&_=20240702194429"
_LISTING_URL = "https://sso.agc.gov.sg/Browse/Act/Current/All?PageSize=500"
_ROBOTS_URL = "https://sso.agc.gov.sg/robots.txt"
_PDF_BODY = b"%PDF-"
_HTML_BODY = b"<html><body>Page not found</body></html>"
_LISTING_BODY = b'<a href="/Act/AA2004?ViewType=Pdf" class="non-ajax file-download">'
_ROBOTS_BODY = b"User-agent: *\nCrawl-delay: 6\nDisallow: /search\n"
_PDF_CONTENT_TYPE = "application/pdf"
_HTML_CONTENT_TYPE = "text/html; charset=utf-8"
_ROBOTS_CONTENT_TYPE = "text/plain"


def _build_source_http_response(
    status_code: int, content_type: Optional[str], body: bytes, requested_url: str
) -> SourceHttpResponse:
    return SourceHttpResponse(
        status_code=status_code,
        requested_url=requested_url,
        final_url=requested_url,
        content_type=content_type,
        body=body,
    )


def _get_pdf_answer(source_http_response: SourceHttpResponse) -> SsoAnswer:
    return get_sso_answer(source_http_response, is_sso_pdf(source_http_response))


def test_a_200_pdf_is_expected() -> None:
    source_http_response = _build_source_http_response(
        200, _PDF_CONTENT_TYPE, _PDF_BODY, _PDF_URL
    )

    assert _get_pdf_answer(source_http_response) == SsoAnswer.EXPECTED


@pytest.mark.parametrize(
    ("status_code", "content_type", "body"),
    [
        (202, None, b""),
        (202, _HTML_CONTENT_TYPE, _HTML_BODY),
        (403, _HTML_CONTENT_TYPE, _HTML_BODY),
        (429, _HTML_CONTENT_TYPE, _HTML_BODY),
        (301, _HTML_CONTENT_TYPE, b""),
        (200, _HTML_CONTENT_TYPE, _HTML_BODY),
    ],
)
def test_a_challenge_raises_naming_the_status(
    status_code: int, content_type: Optional[str], body: bytes
) -> None:
    source_http_response = _build_source_http_response(
        status_code, content_type, body, _PDF_URL
    )

    with pytest.raises(OpenSgLawSsoChallengeError, match=f"SSO answered {status_code}"):
        _get_pdf_answer(source_http_response)


@pytest.mark.parametrize(
    ("status_code", "body"), [(404, _HTML_BODY), (503, _HTML_BODY), (503, b"")]
)
def test_a_404_or_a_5xx_is_a_failure_whatever_its_body(
    status_code: int, body: bytes
) -> None:
    source_http_response = _build_source_http_response(
        status_code, _HTML_CONTENT_TYPE, body, _PDF_URL
    )

    assert _get_pdf_answer(source_http_response) == SsoAnswer.FAILURE


def test_a_listing_page_holding_the_row_marker_is_a_listing_page() -> None:
    source_http_response = _build_source_http_response(
        200, _HTML_CONTENT_TYPE, _LISTING_BODY, _LISTING_URL
    )

    assert is_sso_listing_page(source_http_response)
    assert (
        get_sso_answer(source_http_response, is_sso_listing_page(source_http_response))
        == SsoAnswer.EXPECTED
    )


def test_an_html_page_without_the_row_marker_is_not_a_listing_page() -> None:
    source_http_response = _build_source_http_response(
        200, _HTML_CONTENT_TYPE, _HTML_BODY, _LISTING_URL
    )

    assert not is_sso_listing_page(source_http_response)


def test_a_plain_text_answer_is_a_robots_file() -> None:
    source_http_response = _build_source_http_response(
        200, _ROBOTS_CONTENT_TYPE, _ROBOTS_BODY, _ROBOTS_URL
    )

    assert is_sso_robots_file(source_http_response)
    assert not is_sso_robots_file(
        _build_source_http_response(200, None, _ROBOTS_BODY, _ROBOTS_URL)
    )
