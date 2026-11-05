from sqlmodel import Session

from crud.legislation import CRUDLegislation
from crud.source_response import CRUDSourceResponse
from enums import ResponseKind
from services.legislation import (
    LegislationWrite,
    build_legislation_write,
    get_listings,
)

_HTTP_OK = 200


def get_legislation_write(session: Session) -> LegislationWrite:
    listing_page_rows = CRUDSourceResponse(
        session
    ).get_listing_page_rows_by_kind_and_status_code(ResponseKind.LISTING_PAGE, _HTTP_OK)
    return build_legislation_write(
        get_listings(listing_page_rows), CRUDLegislation(session).get_rows()
    )


def write_legislation(session: Session, legislation_write: LegislationWrite) -> None:
    CRUDLegislation(session).add_many(legislation_write.legislations_to_insert)
    CRUDLegislation(session).update_many(legislation_write.legislation_updates)
