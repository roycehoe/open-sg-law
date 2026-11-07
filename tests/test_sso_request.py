from datetime import datetime
from zoneinfo import ZoneInfo

from services.sso_request import (
    get_act_pdf_paths_to_fetch,
    get_sso_window_status,
    get_sso_window_text,
)
from settings import settings
from utils.sso_listing import SsoListingRow

_SINGAPORE = ZoneInfo("Asia/Singapore")
_AA2004_PDF_PATH = "/Act/AA2004?ViewType=Pdf&_=20240702194429"


def _get_pdf_url(pdf_path: str) -> str:
    return f"{settings.sso_base_url}{pdf_path}"


def test_the_window_text_names_the_start_and_the_cutoff() -> None:
    assert get_sso_window_text() == "03:00 to 06:55 SGT"


def test_the_window_status_gives_the_singapore_time_and_the_window() -> None:
    now = datetime(2026, 11, 6, 4, 30, tzinfo=_SINGAPORE)

    assert (
        get_sso_window_status(now)
        == "It is 04:30 SGT; requests go only from 03:00 to 06:55 SGT"
    )


def test_get_act_pdf_paths_to_fetch_orders_and_skips() -> None:
    listing_rows = [
        SsoListingRow(
            "AA2004", "Accountants Act 2004", _AA2004_PDF_PATH, "20240702194429"
        ),
        SsoListingRow("ZZ1999", "Unstamped Act 1999", "/Act/ZZ1999?ViewType=Pdf", None),
        SsoListingRow("YY2012", "Unlinked Act 2012", None, None),
        SsoListingRow(
            "BB2001",
            "Older Act 2001",
            "/Act/BB2001?ViewType=Pdf&_=20240101000000",
            "20240101000000",
        ),
        SsoListingRow(
            "CC2002",
            "Oldest Act 2002",
            "/Act/CC2002?ViewType=Pdf&_=20240101000000",
            "20240101000000",
        ),
    ]
    stored_document_urls = [
        _get_pdf_url(_AA2004_PDF_PATH),
        _get_pdf_url("/Act/BB2001?ViewType=Pdf&_=20230101000000"),
        f"https://web.archive.org/web/20240716171208id_/{_get_pdf_url('/Act/CC2002?ViewType=Pdf&_=20220101000000')}",
        _get_pdf_url("/Act/CC2002/Historical/20200101?ViewType=Pdf&_=20230601000000"),
    ]

    assert get_act_pdf_paths_to_fetch(listing_rows, stored_document_urls) == [
        "/Act/ZZ1999?ViewType=Pdf",
        "/Act/CC2002?ViewType=Pdf&_=20240101000000",
        "/Act/BB2001?ViewType=Pdf&_=20240101000000",
    ]
