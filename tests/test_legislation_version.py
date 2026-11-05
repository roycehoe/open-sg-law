from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from crud.legislation_version import LegislationVersionRow
from services.legislation_version import (
    PrintedVersionDate,
    get_newest_version_updates,
    get_printed_version_date,
)
from utils.legislation_version_update import LegislationVersionNewestUpdate
from utils.pdf_text import PdfPage, get_pdf_pages

_FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "pdf"
_EARLIER_CAPTURED_AT = datetime(2026, 1, 1, 4, 18, 57, tzinfo=timezone.utc)
_LATER_CAPTURED_AT = datetime(2026, 11, 5, 19, 0, tzinfo=timezone.utc)


def _get_pages(file_name: str) -> list[PdfPage]:
    return get_pdf_pages((_FIXTURE_DIRECTORY / file_name).read_bytes())


def test_the_version_in_force_line_gives_the_date() -> None:
    pdf_pages = _get_pages("IA1965-p5-6.pdf")

    printed_version_date = get_printed_version_date(pdf_pages)

    assert printed_version_date == PrintedVersionDate(
        printed_text="25/11/2024", version_date=date(2024, 11, 25)
    )


def test_a_footer_date_gives_the_date_when_no_line_says_version_in_force() -> None:
    pdf_pages = _get_pages("AA1906-p3-4.pdf")

    printed_version_date = get_printed_version_date(pdf_pages)

    assert printed_version_date == PrintedVersionDate(
        printed_text="31.12.2021", version_date=date(2021, 12, 31)
    )


def test_no_pages_give_no_date() -> None:
    assert get_printed_version_date([]) is None


def _build_row(
    row_id: int,
    legislation_id: int,
    version_date: Optional[date],
    captured_at: datetime,
    is_newest: bool,
) -> LegislationVersionRow:
    return LegislationVersionRow(
        id=row_id,
        legislation_id=legislation_id,
        source_response_id=row_id,
        version_date=version_date,
        captured_at=captured_at,
        is_newest=is_newest,
    )


def test_the_later_printed_date_is_newest_whatever_the_capture_time() -> None:
    legislation_version_rows = [
        _build_row(1, 1, date(2024, 11, 25), _EARLIER_CAPTURED_AT, True),
        _build_row(2, 1, date(2021, 12, 31), _LATER_CAPTURED_AT, False),
    ]

    assert get_newest_version_updates(legislation_version_rows) == []


def test_an_equal_printed_date_goes_to_the_later_capture() -> None:
    legislation_version_rows = [
        _build_row(1, 1, date(2024, 11, 25), _EARLIER_CAPTURED_AT, True),
        _build_row(2, 1, date(2024, 11, 25), _LATER_CAPTURED_AT, False),
    ]

    assert get_newest_version_updates(legislation_version_rows) == [
        LegislationVersionNewestUpdate(id=1, is_newest=False),
        LegislationVersionNewestUpdate(id=2, is_newest=True),
    ]


def test_a_version_with_no_printed_date_loses_to_one_with_a_date() -> None:
    legislation_version_rows = [
        _build_row(1, 1, None, _LATER_CAPTURED_AT, False),
        _build_row(2, 1, date(2021, 12, 31), _EARLIER_CAPTURED_AT, False),
        _build_row(3, 2, None, _EARLIER_CAPTURED_AT, False),
    ]

    assert get_newest_version_updates(legislation_version_rows) == [
        LegislationVersionNewestUpdate(id=2, is_newest=True),
        LegislationVersionNewestUpdate(id=3, is_newest=True),
    ]
