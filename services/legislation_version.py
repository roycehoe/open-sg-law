import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from crud.legislation_version import LegislationVersionRow
from exceptions import OpenSgLawVersionDateError
from utils.legislation_version_update import LegislationVersionNewestUpdate
from utils.pdf_text import PdfPage

_VERSION_IN_FORCE_PATTERN = re.compile(r"version in force from (\d{1,2}/\d{1,2}/\d{4})")
_VERSION_IN_FORCE_FORMAT = "%d/%m/%Y"
_FOOTER_DATE_PATTERN = re.compile(r"^(\d{1,2}\.\d{1,2}\.\d{4})$")
_FOOTER_DATE_FORMAT = "%d.%m.%Y"
_ARCHIVE_CAPTURE_PATTERN = re.compile(r"/web/(\d{14})id_/(.+)$")


@dataclass(frozen=True)
class PrintedVersionDate:
    printed_text: str
    version_date: date


@dataclass(frozen=True)
class ArchiveCapture:
    timestamp: str
    original_url: str


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


def get_archive_capture(requested_url: str) -> Optional[ArchiveCapture]:
    archive_capture_match = _ARCHIVE_CAPTURE_PATTERN.search(requested_url)
    if archive_capture_match is None:
        return None
    return ArchiveCapture(
        timestamp=archive_capture_match.group(1),
        original_url=archive_capture_match.group(2),
    )


def get_newest_version_updates(
    legislation_version_rows: list[LegislationVersionRow],
) -> list[LegislationVersionNewestUpdate]:
    oldest_first_rows = sorted(
        legislation_version_rows,
        key=lambda legislation_version_row: (
            legislation_version_row.version_date or date.min,
            legislation_version_row.captured_at,
        ),
    )
    legislation_id_to_newest_id = {
        legislation_version_row.legislation_id: legislation_version_row.id
        for legislation_version_row in oldest_first_rows
    }
    legislation_version_newest_updates: list[LegislationVersionNewestUpdate] = []
    for legislation_version_row in legislation_version_rows:
        is_newest = (
            legislation_id_to_newest_id[legislation_version_row.legislation_id]
            == legislation_version_row.id
        )
        if legislation_version_row.is_newest != is_newest:
            legislation_version_newest_updates.append(
                LegislationVersionNewestUpdate(
                    id=legislation_version_row.id, is_newest=is_newest
                )
            )
    return legislation_version_newest_updates
