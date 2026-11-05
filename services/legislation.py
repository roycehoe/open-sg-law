from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from crud.legislation import LegislationRow
from crud.source_response import ListingPageRow
from database.legislation import Legislation
from enums import SourceName
from exceptions import OpenSgLawListingParseError
from utils.archive_capture_url import get_archive_capture, get_capture_time
from utils.legislation_update import LegislationUpdate
from utils.sso_listing import (
    SsoListingRow,
    get_sso_listing_page,
    get_sso_listing_page_index,
)


@dataclass(frozen=True)
class Listing:
    listed_at: datetime
    source: SourceName
    rows: list[SsoListingRow]


@dataclass(frozen=True)
class Listings:
    complete_listings: list[Listing]
    incomplete_harvest_run_ids: list[int]


@dataclass(frozen=True)
class PlannedLegislation:
    sso_code: str
    title: str
    is_in_newest_listing: bool
    listing_source: SourceName


@dataclass(frozen=True)
class LegislationWrite:
    legislations_to_insert: list[Legislation]
    legislation_updates: list[LegislationUpdate]
    unchanged_count: int
    incomplete_harvest_run_ids: list[int]


@dataclass(frozen=True)
class _ParsedPage:
    page_index: int
    page_count: int
    listed_at: datetime
    source: SourceName
    rows: list[SsoListingRow]


def _get_listed_at(listing_page_row: ListingPageRow) -> datetime:
    if listing_page_row.source != SourceName.INTERNET_ARCHIVE:
        return listing_page_row.fetched_at
    archive_capture = get_archive_capture(listing_page_row.final_url)
    if archive_capture is None:
        raise OpenSgLawListingParseError(
            f"The archive listing page {listing_page_row.final_url} holds no capture time"
        )
    return get_capture_time(archive_capture.timestamp)


def _get_parsed_page(listing_page_row: ListingPageRow) -> Optional[_ParsedPage]:
    if listing_page_row.body_text is None:
        return None
    try:
        sso_listing_page = get_sso_listing_page(listing_page_row.body_text)
    except OpenSgLawListingParseError:
        return None
    return _ParsedPage(
        page_index=get_sso_listing_page_index(listing_page_row.requested_url),
        page_count=sso_listing_page.page_count,
        listed_at=_get_listed_at(listing_page_row),
        source=listing_page_row.source,
        rows=sso_listing_page.rows,
    )


def _has_every_page(parsed_pages: list[_ParsedPage]) -> bool:
    if not parsed_pages:
        return False
    page_indexes = sorted(parsed_page.page_index for parsed_page in parsed_pages)
    return page_indexes == list(range(parsed_pages[0].page_count))


def get_listings(listing_page_rows: list[ListingPageRow]) -> Listings:
    harvest_run_id_to_page_rows: dict[int, list[ListingPageRow]] = {}
    for listing_page_row in listing_page_rows:
        harvest_run_id_to_page_rows.setdefault(
            listing_page_row.harvest_run_id, []
        ).append(listing_page_row)
    listings: list[Listing] = []
    incomplete_harvest_run_ids: list[int] = []
    for harvest_run_id, page_rows in harvest_run_id_to_page_rows.items():
        parsed_pages = [
            parsed_page
            for parsed_page in map(_get_parsed_page, page_rows)
            if parsed_page is not None
        ]
        if not _has_every_page(parsed_pages):
            incomplete_harvest_run_ids.append(harvest_run_id)
            continue
        listings.append(
            Listing(
                listed_at=min(parsed_page.listed_at for parsed_page in parsed_pages),
                source=parsed_pages[0].source,
                rows=[
                    listing_row
                    for parsed_page in parsed_pages
                    for listing_row in parsed_page.rows
                ],
            )
        )
    return Listings(listings, incomplete_harvest_run_ids)


def build_planned_legislation(listings: list[Listing]) -> list[PlannedLegislation]:
    if not listings:
        return []
    oldest_first = sorted(listings, key=lambda listing: listing.listed_at)
    newest_sso_codes = frozenset(
        listing_row.sso_code for listing_row in oldest_first[-1].rows
    )
    sso_code_to_planned_legislation: dict[str, PlannedLegislation] = {}
    for listing in oldest_first:
        for listing_row in listing.rows:
            sso_code_to_planned_legislation[listing_row.sso_code] = PlannedLegislation(
                sso_code=listing_row.sso_code,
                title=listing_row.title,
                is_in_newest_listing=listing_row.sso_code in newest_sso_codes,
                listing_source=listing.source,
            )
    return sorted(
        sso_code_to_planned_legislation.values(),
        key=lambda planned_legislation: planned_legislation.sso_code,
    )


def build_legislation_write(
    listings: Listings, legislation_rows: list[LegislationRow]
) -> LegislationWrite:
    sso_code_to_legislation_row = {
        legislation_row.sso_code: legislation_row
        for legislation_row in legislation_rows
    }
    legislations_to_insert: list[Legislation] = []
    legislation_updates: list[LegislationUpdate] = []
    unchanged_count = 0
    for planned_legislation in build_planned_legislation(listings.complete_listings):
        legislation_row = sso_code_to_legislation_row.get(planned_legislation.sso_code)
        if legislation_row is None:
            legislations_to_insert.append(
                Legislation(
                    sso_code=planned_legislation.sso_code,
                    title=planned_legislation.title,
                    is_in_newest_listing=planned_legislation.is_in_newest_listing,
                    listing_source=planned_legislation.listing_source,
                )
            )
            continue
        if (
            legislation_row.title != planned_legislation.title
            or legislation_row.is_in_newest_listing
            != planned_legislation.is_in_newest_listing
            or legislation_row.listing_source != planned_legislation.listing_source
        ):
            legislation_updates.append(
                LegislationUpdate(
                    id=legislation_row.id,
                    title=planned_legislation.title,
                    is_in_newest_listing=planned_legislation.is_in_newest_listing,
                    listing_source=planned_legislation.listing_source,
                )
            )
            continue
        unchanged_count += 1
    return LegislationWrite(
        legislations_to_insert=legislations_to_insert,
        legislation_updates=legislation_updates,
        unchanged_count=unchanged_count,
        incomplete_harvest_run_ids=listings.incomplete_harvest_run_ids,
    )
