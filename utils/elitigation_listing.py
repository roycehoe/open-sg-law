import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from exceptions import OpenSgLawListingParseError

_TOTAL_PATTERN = re.compile(r"Total Judgment\(s\) Found\s*:\s*([\d,]+)")
_PAGE_NUMBER_PATTERN = re.compile(r"CurrentPage=(\d+)")
_CITATION_SUFFIX = "|"
_ONLY_PAGE_COUNT = 1


@dataclass(frozen=True)
class ElitigationListingRow:
    judgment_path: str
    neutral_citation: str


@dataclass(frozen=True)
class ElitigationListingPage:
    result_count: int
    page_count: int
    rows: list[ElitigationListingRow]


def _get_listing_row(title_link: Tag) -> ElitigationListingRow:
    judgment_path = title_link.get("href")
    if not isinstance(judgment_path, str):
        raise OpenSgLawListingParseError("A listing row holds no judgment link")
    card = title_link.find_parent("div", class_="card")
    if card is None:
        raise OpenSgLawListingParseError(
            f"The listing row for {judgment_path} sits in no card"
        )
    citation_element = card.select_one("a.citation-num-link span")
    if citation_element is None:
        raise OpenSgLawListingParseError(
            f"The listing row for {judgment_path} holds no neutral citation"
        )
    return ElitigationListingRow(
        judgment_path=judgment_path,
        neutral_citation=citation_element.get_text(strip=True)
        .removesuffix(_CITATION_SUFFIX)
        .strip(),
    )


def _get_page_count(listing_tree: BeautifulSoup) -> int:
    page_numbers = [_ONLY_PAGE_COUNT]
    for page_link in listing_tree.select("ul.pagination li a"):
        link_text = page_link.get_text(strip=True)
        if link_text.isdigit():
            page_numbers.append(int(link_text))
        href = page_link.get("href")
        if not isinstance(href, str):
            continue
        for match in _PAGE_NUMBER_PATTERN.finditer(href):
            page_numbers.append(int(match.group(1)))
    return max(page_numbers)


def get_elitigation_listing_page(listing_html: str) -> ElitigationListingPage:
    listing_tree = BeautifulSoup(listing_html, "html.parser")
    match = _TOTAL_PATTERN.search(listing_tree.get_text())
    if match is None:
        raise OpenSgLawListingParseError("The listing page holds no judgment total")
    return ElitigationListingPage(
        result_count=int(match.group(1).replace(",", "")),
        page_count=_get_page_count(listing_tree),
        rows=[
            _get_listing_row(title_link)
            for title_link in listing_tree.select("a.gd-heardertext")
        ],
    )
