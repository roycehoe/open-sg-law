from datetime import datetime, timezone

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

from crud.legislation import CRUDLegislation
from crud.source_response import ListingPageRow
from enums import SourceName
from exceptions import OpenSgLawListingParseError
from populate.legislation import get_legislation_write, write_legislation
from services.legislation import (
    Listing,
    PlannedLegislation,
    build_planned_legislation,
    get_listings,
)
from tests.document_seed import ARCHIVE_FETCHED_AT, SSO_FETCHED_AT
from tests.listing_seed import (
    FIRST_PAGE_BODY,
    LISTING_CONTENT_TYPE,
    SECOND_PAGE_BODY,
    build_listing_page_row,
    build_listing_page_rows,
    seed_listing,
)
from tests.source_seed import seed_sources
from utils.sso_listing import SsoListingRow, build_sso_listing_url, get_sso_listing_page

_FIRST_PAGE_ROWS = get_sso_listing_page(FIRST_PAGE_BODY.decode("utf-8")).rows
_SECOND_PAGE_ROWS = get_sso_listing_page(SECOND_PAGE_BODY.decode("utf-8")).rows
_ARCHIVE_LISTED_AT = datetime(2024, 7, 16, 23, 42, 18, tzinfo=timezone.utc)
_CODE_COUNT = 6


def test_a_complete_archive_listing_is_listed_at_its_earliest_capture() -> None:
    listing_page_rows = build_listing_page_rows(
        1, SourceName.INTERNET_ARCHIVE, ARCHIVE_FETCHED_AT
    )

    listings = get_listings(listing_page_rows)

    assert listings.incomplete_harvest_run_ids == []
    assert listings.complete_listings == [
        Listing(
            listed_at=_ARCHIVE_LISTED_AT,
            source=SourceName.INTERNET_ARCHIVE,
            rows=[*_FIRST_PAGE_ROWS, *_SECOND_PAGE_ROWS],
        )
    ]


def test_an_sso_listing_is_listed_when_it_was_fetched() -> None:
    listing_page_rows = build_listing_page_rows(2, SourceName.SSO, SSO_FETCHED_AT)

    listings = get_listings(listing_page_rows)

    assert [listing.listed_at for listing in listings.complete_listings] == [
        SSO_FETCHED_AT
    ]
    assert [listing.source for listing in listings.complete_listings] == [
        SourceName.SSO
    ]


def test_a_listing_missing_a_page_is_incomplete_and_gives_no_rows() -> None:
    first_run_without_page_one = build_listing_page_rows(
        1, SourceName.INTERNET_ARCHIVE, ARCHIVE_FETCHED_AT, page_indexes=(1,)
    )
    second_run_without_page_two = build_listing_page_rows(
        2, SourceName.SSO, SSO_FETCHED_AT, page_indexes=(0,)
    )

    listings = get_listings(first_run_without_page_one + second_run_without_page_two)

    assert listings.complete_listings == []
    assert listings.incomplete_harvest_run_ids == [1, 2]


def test_a_page_with_no_text_or_no_result_count_is_left_out() -> None:
    listing_page_rows = [
        build_listing_page_row(
            11, 1, SourceName.SSO, 0, "<html></html>", "", SSO_FETCHED_AT
        ),
        build_listing_page_row(12, 1, SourceName.SSO, 1, None, "", SSO_FETCHED_AT),
    ]

    listings = get_listings(listing_page_rows)

    assert listings.complete_listings == []
    assert listings.incomplete_harvest_run_ids == [1]


def test_an_archive_page_with_no_capture_time_raises() -> None:
    listing_page_row = ListingPageRow(
        id=1,
        requested_url=build_sso_listing_url(0),
        final_url=build_sso_listing_url(0),
        content_type=LISTING_CONTENT_TYPE,
        body_text=FIRST_PAGE_BODY.decode("utf-8"),
        fetched_at=ARCHIVE_FETCHED_AT,
        source=SourceName.INTERNET_ARCHIVE,
        harvest_run_id=1,
    )

    with pytest.raises(OpenSgLawListingParseError, match="holds no capture time"):
        get_listings([listing_page_row])


def test_the_newest_listing_sets_the_source_and_flag_and_older_codes_keep_theirs() -> (
    None
):
    archive_listing = Listing(
        listed_at=_ARCHIVE_LISTED_AT,
        source=SourceName.INTERNET_ARCHIVE,
        rows=[*_FIRST_PAGE_ROWS, *_SECOND_PAGE_ROWS],
    )
    sso_listing = Listing(
        listed_at=SSO_FETCHED_AT,
        source=SourceName.SSO,
        rows=list(_FIRST_PAGE_ROWS),
    )

    planned_legislations = build_planned_legislation([sso_listing, archive_listing])

    assert [
        (
            planned_legislation.sso_code,
            planned_legislation.is_in_newest_listing,
            planned_legislation.listing_source,
        )
        for planned_legislation in planned_legislations
    ] == [
        ("AA2004", True, SourceName.SSO),
        ("ACRAA2004", True, SourceName.SSO),
        ("ASA2007", True, SourceName.SSO),
        ("TA1967", False, SourceName.INTERNET_ARCHIVE),
        ("TCA2005", False, SourceName.INTERNET_ARCHIVE),
        ("UPA1967", False, SourceName.INTERNET_ARCHIVE),
    ]


def test_the_latest_listing_that_shows_a_code_gives_its_title() -> None:
    older_row = SsoListingRow(
        sso_code="AA2004",
        title="Accountants Act",
        pdf_path="/Act/AA2004?ViewType=Pdf",
        version_stamp=None,
    )
    newer_row = SsoListingRow(
        sso_code="AA2004",
        title="Accountants Act 2004",
        pdf_path="/Act/AA2004?ViewType=Pdf",
        version_stamp=None,
    )

    planned_legislations = build_planned_legislation(
        [
            Listing(SSO_FETCHED_AT, SourceName.SSO, [newer_row]),
            Listing(_ARCHIVE_LISTED_AT, SourceName.INTERNET_ARCHIVE, [older_row]),
        ]
    )

    assert planned_legislations == [
        PlannedLegislation(
            sso_code="AA2004",
            title="Accountants Act 2004",
            is_in_newest_listing=True,
            listing_source=SourceName.SSO,
        )
    ]


def test_no_listing_plans_no_legislation() -> None:
    assert build_planned_legislation([]) == []


def test_every_fixture_code_is_planned_for_insert_and_a_second_plan_changes_nothing(
    scratch_session: Session,
) -> None:
    seed_sources(scratch_session)
    seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, ARCHIVE_FETCHED_AT)

    first_write = get_legislation_write(scratch_session)
    write_legislation(scratch_session, first_write)
    scratch_session.commit()
    second_write = get_legislation_write(scratch_session)

    assert [
        legislation.sso_code for legislation in first_write.legislations_to_insert
    ] == [
        "AA2004",
        "ACRAA2004",
        "ASA2007",
        "TA1967",
        "TCA2005",
        "UPA1967",
    ]
    assert first_write.legislation_updates == []
    assert first_write.unchanged_count == 0
    assert CRUDLegislation(scratch_session).get_count() == _CODE_COUNT
    assert second_write.legislations_to_insert == []
    assert second_write.legislation_updates == []
    assert second_write.unchanged_count == _CODE_COUNT


def test_a_stored_row_read_back_in_a_new_session_is_sorted_as_unchanged(
    scratch_engine: Engine, scratch_session: Session
) -> None:
    seed_sources(scratch_session)
    seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, ARCHIVE_FETCHED_AT)
    write_legislation(scratch_session, get_legislation_write(scratch_session))
    scratch_session.commit()

    with Session(scratch_engine) as new_session:
        legislation_rows = CRUDLegislation(new_session).get_rows()
        legislation_write = get_legislation_write(new_session)

    assert isinstance(legislation_rows[0].listing_source, str)
    assert legislation_rows[0].listing_source == SourceName.INTERNET_ARCHIVE
    assert legislation_write.legislations_to_insert == []
    assert legislation_write.legislation_updates == []
    assert legislation_write.unchanged_count == _CODE_COUNT


def test_a_newer_sso_listing_updates_the_source_of_every_stored_code(
    scratch_session: Session,
) -> None:
    seed_sources(scratch_session)
    seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, ARCHIVE_FETCHED_AT)
    write_legislation(scratch_session, get_legislation_write(scratch_session))
    scratch_session.commit()
    seed_listing(scratch_session, SourceName.SSO, SSO_FETCHED_AT)

    legislation_write = get_legislation_write(scratch_session)
    write_legislation(scratch_session, legislation_write)
    scratch_session.commit()

    assert legislation_write.legislations_to_insert == []
    assert len(legislation_write.legislation_updates) == _CODE_COUNT
    assert legislation_write.unchanged_count == 0
    assert {
        legislation_row.listing_source
        for legislation_row in CRUDLegislation(scratch_session).get_rows()
    } == {SourceName.SSO}


def test_an_incomplete_listing_run_is_reported_and_marks_no_code_as_dropped(
    scratch_session: Session,
) -> None:
    seed_sources(scratch_session)
    seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, ARCHIVE_FETCHED_AT)
    write_legislation(scratch_session, get_legislation_write(scratch_session))
    scratch_session.commit()
    seed_listing(scratch_session, SourceName.SSO, SSO_FETCHED_AT, page_indexes=(0,))

    legislation_write = get_legislation_write(scratch_session)

    assert legislation_write.incomplete_harvest_run_ids == [2]
    assert legislation_write.legislation_updates == []
    assert legislation_write.unchanged_count == _CODE_COUNT
