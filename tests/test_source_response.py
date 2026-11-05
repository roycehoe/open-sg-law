import hashlib
from typing import Optional

from sqlmodel import Session, func, select

from crud.harvest_run import CRUDHarvestRun
from crud.source_response import CRUDSourceResponse
from database.harvest_run import HarvestRun
from database.source_response import SourceResponse
from enums import ResponseKind, SourceName
from schemas.source_http_response import SourceHttpResponse
from services.source_response import build_source_response
from tests.source_seed import seed_sources

_REQUESTED_URL = "https://source.test/Browse/Act/Current/All?PageIndex=2"
_HTML_BODY = "<p>Road Traffic Act 1961</p>".encode("utf-8")
_HTML_CONTENT_TYPE = "text/html; charset=utf-8"
_HTTP_OK = 200
_HARVEST_RUN_ID = 1
_TWO_BODIES_COUNT = 2


def _build_source_http_response(
    body: bytes, content_type: Optional[str]
) -> SourceHttpResponse:
    return SourceHttpResponse(
        status_code=_HTTP_OK,
        requested_url=_REQUESTED_URL,
        final_url=_REQUESTED_URL,
        content_type=content_type,
        body=body,
    )


def _build(body: bytes, content_type: Optional[str]) -> SourceResponse:
    return build_source_response(
        _build_source_http_response(body, content_type),
        ResponseKind.LISTING_PAGE,
        SourceName.SSO,
        _HARVEST_RUN_ID,
    )


def test_an_html_body_with_a_utf_8_charset_is_text() -> None:
    source_response = _build(_HTML_BODY, _HTML_CONTENT_TYPE)

    assert source_response.body_text == "<p>Road Traffic Act 1961</p>"
    assert source_response.body_bytes is None


def test_a_latin_1_body_decodes_by_its_declared_charset() -> None:
    source_response = _build(b"Caf\xe9", "text/html; charset=iso-8859-1")

    assert source_response.body_text == "Café"
    assert source_response.body_bytes is None


def test_invalid_utf_8_with_no_charset_is_bytes() -> None:
    body = b"\xff\xfe broken"

    source_response = _build(body, "text/html")

    assert source_response.body_text is None
    assert source_response.body_bytes == body


def test_a_body_holding_a_nul_is_bytes() -> None:
    body = b"text\x00more"

    source_response = _build(body, _HTML_CONTENT_TYPE)

    assert source_response.body_text is None
    assert source_response.body_bytes == body


def test_a_pdf_signature_is_bytes_whatever_the_content_type() -> None:
    body = b"%PDF-1.4 plain ascii"

    source_response = _build(body, _HTML_CONTENT_TYPE)

    assert source_response.body_text is None
    assert source_response.body_bytes == body


def test_an_unknown_charset_is_bytes() -> None:
    source_response = _build(_HTML_BODY, "text/html; charset=x-unknown")

    assert source_response.body_text is None
    assert source_response.body_bytes == _HTML_BODY


def test_sha256_and_byte_length_describe_the_exact_bytes() -> None:
    body = b"\xff\xfe broken"

    source_response = _build(body, None)

    assert source_response.sha256 == hashlib.sha256(body).hexdigest()
    assert source_response.byte_length == len(body)


def _add_harvest_run(session: Session) -> int:
    seed_sources(session)
    harvest_run = HarvestRun(source=SourceName.SSO)
    CRUDHarvestRun(session).create(harvest_run)
    assert harvest_run.id is not None
    return harvest_run.id


def _insert(session: Session, body: bytes, harvest_run_id: int) -> bool:
    return CRUDSourceResponse(session).insert_on_conflict_do_nothing(
        build_source_response(
            _build_source_http_response(body, _HTML_CONTENT_TYPE),
            ResponseKind.LISTING_PAGE,
            SourceName.SSO,
            harvest_run_id,
        )
    )


def _get_source_response_count(session: Session) -> int:
    return session.exec(select(func.count()).select_from(SourceResponse)).one()


def test_the_same_url_and_body_is_stored_once(scratch_session: Session) -> None:
    harvest_run_id = _add_harvest_run(scratch_session)

    is_first_stored = _insert(scratch_session, _HTML_BODY, harvest_run_id)
    is_second_stored = _insert(scratch_session, _HTML_BODY, harvest_run_id)
    scratch_session.commit()

    assert is_first_stored
    assert not is_second_stored
    assert _get_source_response_count(scratch_session) == 1


def test_the_same_url_with_another_body_adds_a_row(scratch_session: Session) -> None:
    harvest_run_id = _add_harvest_run(scratch_session)

    is_first_stored = _insert(scratch_session, _HTML_BODY, harvest_run_id)
    is_second_stored = _insert(scratch_session, b"<p>Changed</p>", harvest_run_id)
    scratch_session.commit()

    assert is_first_stored
    assert is_second_stored
    assert _get_source_response_count(scratch_session) == _TWO_BODIES_COUNT
