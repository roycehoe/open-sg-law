from pathlib import Path

import pytest

from exceptions import OpenSgLawCdxAnswerError
from services.archive_capture import (
    CdxCapture,
    get_cdx_captures,
    get_latest_act_captures,
)
from tests.listing_seed import OFFLINE_PAGE_BODY

_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"
_CLTPA_ANSWER_TEXT = (
    _FIXTURES_DIRECTORY / "cdx" / "cdx-cltpa-pdf-trimmed.json"
).read_text()
_BILLS_BROWSE_ANSWER_TEXT = (
    _FIXTURES_DIRECTORY / "cdx" / "cdx-bills-browse-trimmed.json"
).read_text()
_CLTPA_CAPTURE_COUNT = 4
_FIRST_CLTPA_DIGEST = "ST4T5OCMSOIHZSYDRKHU4RJUYRZOSXEH"
_ACT_URL_PREFIX = "https://sso.agc.gov.sg/Act/"
_AA1906_URL = f"{_ACT_URL_PREFIX}AA1906?ViewType=Pdf&_=20240203013120"
_AA2001_EARLIER_URL = f"{_ACT_URL_PREFIX}AA2001?ViewType=Pdf&_=20231229163706"
_AA2001_LATER_URL = f"{_ACT_URL_PREFIX}AA2001?ViewType=Pdf&_=20250403160141"
_AA2004_PLAIN_URL = f"{_ACT_URL_PREFIX}AA2004?ViewType=Pdf&_=20250102161905"
_AA2004_VALID_DATE_URL = (
    f"{_ACT_URL_PREFIX}AA2004?ValidDate=20231215&ViewType=Pdf&_=20241025190029"
)
_AA1906_TIMESTAMP = "20251231140314"
_AA2001_EARLIER_TIMESTAMP = "20250430031007"
_AA2001_LATER_TIMESTAMP = "20251231140335"
_AA2004_PLAIN_TIMESTAMP = "20250115082458"
_AA2004_VALID_DATE_TIMESTAMP = "20250121122115"
_ANSWER_WITHOUT_DIGEST_TEXT = '[["original","timestamp"]]'
_ANSWER_WITH_SHORT_ROW_TEXT = (
    '[["original","timestamp","digest"],["https://sso.agc.gov.sg/Act/AA2004"]]'
)


def _build_capture(original_url: str, timestamp: str) -> CdxCapture:
    return CdxCapture(original_url=original_url, timestamp=timestamp, digest="")


def test_the_cltpa_answer_gives_four_captures_with_their_digests() -> None:
    cdx_captures = get_cdx_captures(_CLTPA_ANSWER_TEXT)

    assert len(cdx_captures) == _CLTPA_CAPTURE_COUNT
    assert cdx_captures[0].digest == _FIRST_CLTPA_DIGEST
    assert cdx_captures[0].timestamp == "20190509061656"
    assert cdx_captures[0].original_url == (
        "https://sso.agc.gov.sg/Act/CLTPA1955/Historical/20140310"
        "?DocDate=20000701&ValidDate=20140310&ViewType=Pdf&_=20181004162547"
    )


def test_every_cltpa_capture_is_a_historical_version() -> None:
    assert get_latest_act_captures(get_cdx_captures(_CLTPA_ANSWER_TEXT)) == []


def test_the_bills_browse_answer_holds_no_act_capture() -> None:
    assert get_latest_act_captures(get_cdx_captures(_BILLS_BROWSE_ANSWER_TEXT)) == []


def test_the_offline_page_is_not_a_cdx_answer() -> None:
    with pytest.raises(OpenSgLawCdxAnswerError, match="not a JSON list of rows"):
        get_cdx_captures(OFFLINE_PAGE_BODY.decode("utf-8"))


def test_an_empty_list_is_an_answer_with_no_captures() -> None:
    assert get_cdx_captures("[]") == []


def test_a_header_without_digest_raises() -> None:
    with pytest.raises(OpenSgLawCdxAnswerError, match="no digest field"):
        get_cdx_captures(_ANSWER_WITHOUT_DIGEST_TEXT)


def test_the_latest_plain_capture_of_each_code_wins_in_code_order() -> None:
    cdx_captures = [
        _build_capture(_AA2004_VALID_DATE_URL, _AA2004_VALID_DATE_TIMESTAMP),
        _build_capture(_AA2004_PLAIN_URL, _AA2004_PLAIN_TIMESTAMP),
        _build_capture(_AA2001_LATER_URL, _AA2001_LATER_TIMESTAMP),
        _build_capture(_AA2001_EARLIER_URL, _AA2001_EARLIER_TIMESTAMP),
        _build_capture(_AA1906_URL, _AA1906_TIMESTAMP),
    ]

    assert get_latest_act_captures(cdx_captures) == [
        _build_capture(_AA1906_URL, _AA1906_TIMESTAMP),
        _build_capture(_AA2001_LATER_URL, _AA2001_LATER_TIMESTAMP),
        _build_capture(_AA2004_PLAIN_URL, _AA2004_PLAIN_TIMESTAMP),
    ]


def test_a_later_capture_replaces_an_earlier_one_whatever_the_input_order() -> None:
    cdx_captures = [
        _build_capture(_AA2001_EARLIER_URL, _AA2001_EARLIER_TIMESTAMP),
        _build_capture(_AA2001_LATER_URL, _AA2001_LATER_TIMESTAMP),
    ]

    assert get_latest_act_captures(cdx_captures) == [
        _build_capture(_AA2001_LATER_URL, _AA2001_LATER_TIMESTAMP)
    ]


def test_a_row_shorter_than_the_header_is_refused() -> None:
    with pytest.raises(OpenSgLawCdxAnswerError, match="shorter than its header"):
        get_cdx_captures(_ANSWER_WITH_SHORT_ROW_TEXT)
