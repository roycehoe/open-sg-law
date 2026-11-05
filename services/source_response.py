import hashlib
from typing import Optional

from database.source_response import SourceResponse
from enums import ResponseKind, SourceName
from schemas.source_http_response import SourceHttpResponse

_PDF_SIGNATURE = b"%PDF-"
_PDF_CONTENT_TYPE = "application/pdf"
_CHARSET_PARAMETER_NAME = "charset"
_DEFAULT_CHARSET = "utf-8"
_NUL = "\x00"


def _get_charset(content_type: Optional[str]) -> str:
    if content_type is None:
        return _DEFAULT_CHARSET
    for parameter in content_type.split(";")[1:]:
        name, _separator, value = parameter.strip().partition("=")
        if name.lower() == _CHARSET_PARAMETER_NAME:
            return value.strip().strip('"')
    return _DEFAULT_CHARSET


def _is_pdf(body: bytes, content_type: Optional[str]) -> bool:
    if body.startswith(_PDF_SIGNATURE):
        return True
    if content_type is None:
        return False
    return content_type.lower().startswith(_PDF_CONTENT_TYPE)


def get_body_text(body: bytes, content_type: Optional[str]) -> Optional[str]:
    if _is_pdf(body, content_type):
        return None
    try:
        text = body.decode(_get_charset(content_type))
    except UnicodeDecodeError:
        return None
    except LookupError:
        return None
    if _NUL in text:
        return None
    return text


def build_source_response(
    source_http_response: SourceHttpResponse,
    kind: ResponseKind,
    source: SourceName,
    harvest_run_id: int,
) -> SourceResponse:
    body_text = get_body_text(
        source_http_response.body, source_http_response.content_type
    )
    return SourceResponse(
        requested_url=source_http_response.requested_url,
        final_url=source_http_response.final_url,
        status_code=source_http_response.status_code,
        content_type=source_http_response.content_type,
        body_text=body_text,
        body_bytes=None if body_text is not None else source_http_response.body,
        sha256=hashlib.sha256(source_http_response.body).hexdigest(),
        byte_length=len(source_http_response.body),
        kind=kind,
        source=source,
        harvest_run_id=harvest_run_id,
    )
