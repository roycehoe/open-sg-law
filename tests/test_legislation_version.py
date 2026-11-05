from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from exceptions import OpenSgLawVersionDateError
from services.legislation_version import PrintedVersionDate, get_printed_version_date
from utils.pdf_text import PdfPage, get_pdf_pages

_FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "pdf"


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


def test_a_printed_date_that_is_not_a_calendar_date_raises() -> None:
    pdf_pages = _get_pages("IA1965-p5-6.pdf")
    impossible_pages = [
        replace(
            pdf_page,
            lines=[
                replace(line, text=line.text.replace("25/11/2024", "31/2/2024"))
                for line in pdf_page.lines
            ],
        )
        for pdf_page in pdf_pages
    ]

    with pytest.raises(
        OpenSgLawVersionDateError, match="The PDF prints 31/2/2024, which is not a date"
    ):
        get_printed_version_date(impossible_pages)
