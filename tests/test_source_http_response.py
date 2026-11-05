from typing import Optional

import requests

from gateway.http import build_source_http_response

_REQUESTED_URL = "https://source.test/Act/AA2004?ViewType=Pdf"
_FINAL_URL = "https://source.test/Act/AA2004?ViewType=Pdf&_=20240702194429"
_CONTENT_TYPE = "application/pdf"
_BODY = b"%PDF-1.4 \x00\xff exact bytes"
_HTTP_OK = 200


def _build_response(content_type: Optional[str]) -> requests.Response:
    response = requests.Response()
    response._content = _BODY
    response.status_code = _HTTP_OK
    response.url = _FINAL_URL
    if content_type is not None:
        response.headers["Content-Type"] = content_type
    return response


def test_a_response_keeps_its_values_and_exact_bytes() -> None:
    source_http_response = build_source_http_response(
        _REQUESTED_URL, _build_response(_CONTENT_TYPE)
    )

    assert source_http_response.status_code == _HTTP_OK
    assert source_http_response.requested_url == _REQUESTED_URL
    assert source_http_response.final_url == _FINAL_URL
    assert source_http_response.content_type == _CONTENT_TYPE
    assert source_http_response.body == _BODY


def test_a_response_with_no_content_type_has_none() -> None:
    source_http_response = build_source_http_response(
        _REQUESTED_URL, _build_response(None)
    )

    assert source_http_response.content_type is None
