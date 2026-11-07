from pathlib import Path

import pytest

from exceptions import OpenSgLawListingParseError
from utils.elitigation_judgment import get_elitigation_neutral_citation
from utils.elitigation_listing import (
    ElitigationListingRow,
    get_elitigation_listing_page,
)

_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures" / "elitigation"
_FIRST_PAGE_HTML = (_FIXTURES_DIRECTORY / "supct-2025-page-1.html").read_text()
_LAST_PAGE_HTML = (_FIXTURES_DIRECTORY / "supct-2025-page-58.html").read_text()
_SYSTEM_ERROR_HTML = (
    _FIXTURES_DIRECTORY / "statect-2025-system-error.html"
).read_text()
_JUDGMENT_HTML = (_FIXTURES_DIRECTORY / "judgment-2025-sghc-267.html").read_text()
_DISTRICT_COURT_JUDGMENT_HTML = (
    _FIXTURES_DIRECTORY / "judgment-2026-sgdc-361.html"
).read_text()
_YEAR_TOTAL = 573
_YEAR_PAGE_COUNT = 58
_FULL_PAGE_ROW_COUNT = 10
_LAST_PAGE_ROW_COUNT = 3


def test_the_first_page_gives_the_total_the_page_count_and_ten_rows() -> None:
    listing_page = get_elitigation_listing_page(_FIRST_PAGE_HTML)

    assert listing_page.result_count == _YEAR_TOTAL
    assert listing_page.page_count == _YEAR_PAGE_COUNT
    assert len(listing_page.rows) == _FULL_PAGE_ROW_COUNT
    assert listing_page.rows[0] == ElitigationListingRow(
        judgment_path="/gd/s/2025_SGHC_267", neutral_citation="[2025] SGHC 267"
    )


def test_a_citation_is_kept_as_the_listing_prints_it() -> None:
    listing_page = get_elitigation_listing_page(_FIRST_PAGE_HTML)

    assert listing_page.rows[1] == ElitigationListingRow(
        judgment_path="/gd/s/2025_SGHCA_26", neutral_citation="[2025] SGHC(A) 26"
    )


def test_the_last_page_gives_the_same_page_count_and_three_rows() -> None:
    listing_page = get_elitigation_listing_page(_LAST_PAGE_HTML)

    assert listing_page.result_count == _YEAR_TOTAL
    assert listing_page.page_count == _YEAR_PAGE_COUNT
    assert [row.judgment_path for row in listing_page.rows] == [
        "/gd/s/2025_SGHC_2",
        "/gd/s/2025_SGHC_1",
        "/gd/s/2025_SGCA_1",
    ]
    assert len(listing_page.rows) == _LAST_PAGE_ROW_COUNT


def test_the_system_error_page_raises() -> None:
    with pytest.raises(OpenSgLawListingParseError, match="no judgment total"):
        get_elitigation_listing_page(_SYSTEM_ERROR_HTML)


def test_a_judgment_page_gives_its_neutral_citation() -> None:
    assert get_elitigation_neutral_citation(_JUDGMENT_HTML) == "[2025] SGHC 267"


def test_a_district_court_page_gives_the_citation_in_its_title() -> None:
    assert (
        get_elitigation_neutral_citation(_DISTRICT_COURT_JUDGMENT_HTML)
        == "[2026] SGDC 361"
    )


def test_a_listing_page_gives_no_neutral_citation() -> None:
    assert get_elitigation_neutral_citation(_FIRST_PAGE_HTML) is None


def test_a_page_without_a_neutral_citation_gives_none() -> None:
    assert get_elitigation_neutral_citation(_SYSTEM_ERROR_HTML) is None
