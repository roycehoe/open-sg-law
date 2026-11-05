import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from exceptions import OpenSgLawVersionDateError
from utils.pdf_text import PdfPage

_VERSION_IN_FORCE_PATTERN = re.compile(r"version in force from (\d{1,2}/\d{1,2}/\d{4})")
_VERSION_IN_FORCE_FORMAT = "%d/%m/%Y"
_FOOTER_DATE_PATTERN = re.compile(r"^(\d{1,2}\.\d{1,2}\.\d{4})$")
_FOOTER_DATE_FORMAT = "%d.%m.%Y"


@dataclass(frozen=True)
class PrintedVersionDate:
    printed_text: str
    version_date: date


def _get_version_date(printed_text: str, date_format: str) -> date:
    try:
        return datetime.strptime(printed_text, date_format).date()
    except ValueError as error:
        raise OpenSgLawVersionDateError(
            f"The PDF prints {printed_text}, which is not a date"
        ) from error


def get_printed_version_date(pdf_pages: list[PdfPage]) -> Optional[PrintedVersionDate]:
    margin_texts = [
        line.text for pdf_page in pdf_pages for line in pdf_page.lines if line.is_margin
    ]
    for margin_text in margin_texts:
        version_in_force_match = _VERSION_IN_FORCE_PATTERN.search(margin_text)
        if version_in_force_match is not None:
            printed_text = version_in_force_match.group(1)
            return PrintedVersionDate(
                printed_text=printed_text,
                version_date=_get_version_date(printed_text, _VERSION_IN_FORCE_FORMAT),
            )
    for margin_text in margin_texts:
        footer_date_match = _FOOTER_DATE_PATTERN.match(margin_text)
        if footer_date_match is not None:
            printed_text = footer_date_match.group(1)
            return PrintedVersionDate(
                printed_text=printed_text,
                version_date=_get_version_date(printed_text, _FOOTER_DATE_FORMAT),
            )
    return None
