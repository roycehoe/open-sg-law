from dataclasses import dataclass

from sqlmodel import Session

from crud.legislation import CRUDLegislation
from crud.source_response import CRUDSourceResponse
from database.legislation import Legislation
from enums import ResponseKind
from services.legislation import build_planned_legislation, get_listings
from utils.legislation_update import LegislationUpdate

_HTTP_OK = 200


@dataclass(frozen=True)
class LegislationWrite:
    legislations_to_insert: list[Legislation]
    legislation_updates: list[LegislationUpdate]
    unchanged_count: int
    incomplete_harvest_run_ids: list[int]


def get_legislation_write(session: Session) -> LegislationWrite:
    listing_page_rows = CRUDSourceResponse(
        session
    ).get_listing_page_rows_by_kind_and_status_code(ResponseKind.LISTING_PAGE, _HTTP_OK)
    listings = get_listings(listing_page_rows)
    sso_code_to_legislation_row = {
        legislation_row.sso_code: legislation_row
        for legislation_row in CRUDLegislation(session).get_rows()
    }
    legislations_to_insert: list[Legislation] = []
    legislation_updates: list[LegislationUpdate] = []
    unchanged_count = 0
    for planned_legislation in build_planned_legislation(listings.listings):
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


def write_legislation(session: Session, legislation_write: LegislationWrite) -> None:
    CRUDLegislation(session).add_many(legislation_write.legislations_to_insert)
    CRUDLegislation(session).update_many(legislation_write.legislation_updates)
