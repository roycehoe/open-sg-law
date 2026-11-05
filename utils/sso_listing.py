import re
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup, Tag

from exceptions import OpenSgLawListingParseError
from utils.sso_act_url import get_sso_act_pdf

_PAGE_COUNT_PATTERN = re.compile(r"([\d,]+) results? in (\d+) pages?")
_ACT_TITLE_PATH_PATTERN = re.compile(r"^/Act/[^/?#]+$")
_TITLE_LINK_CLASS = "non-ajax"
_LATER_PAGE_PATTERN = re.compile(r"/Browse/Act/Current/All/(\d+)\?")


@dataclass(frozen=True)
class SsoListingRow:
    sso_code: str
    title: str
    pdf_path: str
    version_stamp: Optional[str]


@dataclass(frozen=True)
class SsoListingPage:
    result_count: int
    page_count: int
    rows: list[SsoListingRow]


def get_sso_listing_page_index(url: str) -> int:
    match = _LATER_PAGE_PATTERN.search(url)
    if match is None:
        return 0
    return int(match.group(1))


def _get_listing_row(table_row: Tag) -> Optional[SsoListingRow]:
    first_cell = table_row.select_one("td")
    if first_cell is None:
        return None
    title_link = first_cell.select_one("a")
    if title_link is None:
        return None
    if title_link.get("class") != [_TITLE_LINK_CLASS]:
        return None
    title_path = title_link.get("href")
    if not isinstance(title_path, str):
        return None
    if _ACT_TITLE_PATH_PATTERN.match(title_path) is None:
        return None
    _act_path, _slash, sso_code = title_path.rpartition("/")
    pdf_link = table_row.select_one("td.hidden-xs a.file-download")
    if pdf_link is None:
        raise OpenSgLawListingParseError(
            f"The listing row for {sso_code} holds no PDF link"
        )
    pdf_path = pdf_link.get("href")
    if not isinstance(pdf_path, str):
        raise OpenSgLawListingParseError(
            f"The listing row for {sso_code} holds no PDF link"
        )
    sso_act_pdf = get_sso_act_pdf(pdf_path)
    if sso_act_pdf is None:
        raise OpenSgLawListingParseError(
            f"The listing row for {sso_code} holds no PDF link"
        )
    return SsoListingRow(
        sso_code=sso_code,
        title=title_link.get_text(strip=True),
        pdf_path=pdf_path,
        version_stamp=sso_act_pdf.version_stamp,
    )


def get_sso_listing_page(listing_html: str) -> SsoListingPage:
    listing_tree = BeautifulSoup(listing_html, "html.parser")
    page_count_element = listing_tree.select_one("div.page-count")
    if page_count_element is None:
        raise OpenSgLawListingParseError("The listing page holds no result count")
    match = _PAGE_COUNT_PATTERN.search(page_count_element.get_text())
    if match is None:
        raise OpenSgLawListingParseError("The listing page holds no result count")
    listing_rows = [
        _get_listing_row(table_row) for table_row in listing_tree.select("tr")
    ]
    return SsoListingPage(
        result_count=int(match.group(1).replace(",", "")),
        page_count=int(match.group(2)),
        rows=[listing_row for listing_row in listing_rows if listing_row is not None],
    )
