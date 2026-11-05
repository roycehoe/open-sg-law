from pathlib import Path

import pytest

from exceptions import OpenSgLawListingParseError
from gateway.sso import build_sso_listing_url
from utils.sso_listing import (
    SsoListingRow,
    get_sso_listing_page,
    get_sso_listing_page_index,
)

_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"
_FIRST_LISTING_FILE = (
    _FIXTURES_DIRECTORY / "sso_listing" / "browse-all-p1-20240716-trimmed.html"
)
_SECOND_LISTING_FILE = (
    _FIXTURES_DIRECTORY / "sso_listing" / "browse-all-p2-20240719-trimmed.html"
)
_OFFLINE_FILE = _FIXTURES_DIRECTORY / "archive" / "temporarily-offline-20261104.html"
_PRINTED_RESULT_COUNT = 523
_PRINTED_PAGE_COUNT = 2
_ARCHIVE_SECOND_LISTING_URL = "https://web.archive.org/web/20240719042908id_/https://sso.agc.gov.sg/Browse/Act/Current/All/1?PageSize=500&SortBy=Title&SortOrder=ASC"


def test_the_first_listing_page_gives_its_count_and_rows_as_printed() -> None:
    sso_listing_page = get_sso_listing_page(
        _FIRST_LISTING_FILE.read_text(encoding="utf-8")
    )

    assert sso_listing_page.result_count == _PRINTED_RESULT_COUNT
    assert sso_listing_page.page_count == _PRINTED_PAGE_COUNT
    assert sso_listing_page.rows == [
        SsoListingRow(
            sso_code="AA2004",
            title="Accountants Act 2004",
            pdf_path="/Act/AA2004?ViewType=Pdf&_=20240702194429",
            version_stamp="20240702194429",
        ),
        SsoListingRow(
            sso_code="ACRAA2004",
            title="Accounting and Corporate Regulatory Authority Act 2004",
            pdf_path="/Act/ACRAA2004?ViewType=Pdf&_=20230613004057",
            version_stamp="20230613004057",
        ),
        SsoListingRow(
            sso_code="ASA2007",
            title="Accounting Standards Act 2007",
            pdf_path="/Act/ASA2007?ViewType=Pdf&_=20230401031605",
            version_stamp="20230401031605",
        ),
    ]


def test_the_second_listing_page_holds_the_trust_companies_act() -> None:
    sso_listing_page = get_sso_listing_page(
        _SECOND_LISTING_FILE.read_text(encoding="utf-8")
    )

    assert sso_listing_page.page_count == _PRINTED_PAGE_COUNT
    assert (
        SsoListingRow(
            sso_code="TCA2005",
            title="Trust Companies Act 2005",
            pdf_path="/Act/TCA2005?ViewType=Pdf&_=20240718005803",
            version_stamp="20240718005803",
        )
        in sso_listing_page.rows
    )


def test_the_archive_offline_page_is_not_a_listing() -> None:
    with pytest.raises(OpenSgLawListingParseError, match="no result count"):
        get_sso_listing_page(_OFFLINE_FILE.read_text(encoding="utf-8"))


def test_the_page_index_is_read_from_sso_and_archive_urls() -> None:
    assert get_sso_listing_page_index(build_sso_listing_url(0)) == 0
    assert get_sso_listing_page_index(build_sso_listing_url(1)) == 1
    assert get_sso_listing_page_index(_ARCHIVE_SECOND_LISTING_URL) == 1
