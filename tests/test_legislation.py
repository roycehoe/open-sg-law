from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session

from crud.harvest_run import CRUDHarvestRun
from crud.legislation import CRUDLegislation
from crud.source_response import CRUDSourceResponse, ListingPageRow
from database.harvest_run import HarvestRun
from enums import HarvestRunStatus, ResponseKind, SourceName
from exceptions import OpenSgLawListingParseError
from gateway.internet_archive import build_archive_capture_url
from gateway.sso import build_sso_listing_url
from populate.legislation import get_legislation_write, write_legislation
from schemas.source_http_response import SourceHttpResponse
from services.legislation import (
    Listing,
    PlannedLegislation,
    build_planned_legislation,
    get_listings,
)
from services.source_response import build_source_response
from tests.source_seed import seed_sources
from utils.sso_listing import SsoListingRow, get_sso_listing_page

_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures" / "sso_listing"
_FIRST_PAGE_BODY = (
    _FIXTURES_DIRECTORY / "browse-all-p1-20240716-trimmed.html"
).read_bytes()
_SECOND_PAGE_BODY = (
    _FIXTURES_DIRECTORY / "browse-all-p2-20240719-trimmed.html"
).read_bytes()
_FIRST_PAGE_ROWS = get_sso_listing_page(_FIRST_PAGE_BODY.decode("utf-8")).rows
_SECOND_PAGE_ROWS = get_sso_listing_page(_SECOND_PAGE_BODY.decode("utf-8")).rows
_FIRST_CAPTURE_TIMESTAMP = "20240716234218"
_SECOND_CAPTURE_TIMESTAMP = "20240719042908"
_ARCHIVE_LISTED_AT = datetime(2024, 7, 16, 23, 42, 18, tzinfo=timezone.utc)
_SSO_FETCHED_AT = datetime(2026, 11, 5, 19, 0, tzinfo=timezone.utc)
_ARCHIVE_FETCHED_AT = datetime(2026, 11, 5, 18, 0, tzinfo=timezone.utc)
_LISTING_CONTENT_TYPE = "text/html; charset=utf-8"
_PAGE_COUNT = 2
_CODE_COUNT = 6


def _build_listing_page_row(
    page_id: int,
    harvest_run_id: int,
    source: SourceName,
    page_index: int,
    body_text: Optional[str],
    capture_timestamp: str,
    fetched_at: datetime,
) -> ListingPageRow:
    sso_url = build_sso_listing_url(page_index)
    requested_url = (
        build_archive_capture_url(capture_timestamp, sso_url)
        if source == SourceName.INTERNET_ARCHIVE
        else sso_url
    )
    return ListingPageRow(
        id=page_id,
        requested_url=requested_url,
        final_url=requested_url,
        content_type=_LISTING_CONTENT_TYPE,
        body_text=body_text,
        fetched_at=fetched_at,
        source=source,
        harvest_run_id=harvest_run_id,
    )


def _build_listing_page_rows(
    harvest_run_id: int,
    source: SourceName,
    fetched_at: datetime,
    page_indexes: tuple[int, ...] = (0, 1),
) -> list[ListingPageRow]:
    page_index_to_body = {
        0: _FIRST_PAGE_BODY.decode("utf-8"),
        1: _SECOND_PAGE_BODY.decode("utf-8"),
    }
    page_index_to_timestamp = {
        0: _FIRST_CAPTURE_TIMESTAMP,
        1: _SECOND_CAPTURE_TIMESTAMP,
    }
    return [
        _build_listing_page_row(
            page_id=harvest_run_id * 10 + page_index,
            harvest_run_id=harvest_run_id,
            source=source,
            page_index=page_index,
            body_text=page_index_to_body[page_index],
            capture_timestamp=page_index_to_timestamp[page_index],
            fetched_at=fetched_at,
        )
        for page_index in page_indexes
    ]


def _seed_listing(
    session: Session,
    source: SourceName,
    fetched_at: datetime,
    page_indexes: tuple[int, ...] = (0, 1),
) -> None:
    harvest_run = HarvestRun(
        source=source, status=HarvestRunStatus.SUCCEEDED, started_at=fetched_at
    )
    CRUDHarvestRun(session).create(harvest_run)
    assert harvest_run.id is not None
    for page_row in _build_listing_page_rows(
        harvest_run.id, source, fetched_at, page_indexes
    ):
        source_response = build_source_response(
            SourceHttpResponse(
                status_code=200,
                requested_url=page_row.requested_url,
                final_url=page_row.final_url,
                content_type=page_row.content_type,
                body=(page_row.body_text or "").encode("utf-8"),
            ),
            ResponseKind.LISTING_PAGE,
            source,
            harvest_run.id,
        )
        source_response.fetched_at = fetched_at
        CRUDSourceResponse(session).insert_on_conflict_do_nothing(source_response)
    session.commit()


def test_a_complete_archive_listing_is_listed_at_its_earliest_capture() -> None:
    listing_page_rows = _build_listing_page_rows(
        1, SourceName.INTERNET_ARCHIVE, _ARCHIVE_FETCHED_AT
    )

    listings = get_listings(listing_page_rows)

    assert listings.incomplete_harvest_run_ids == []
    assert listings.listings == [
        Listing(
            listed_at=_ARCHIVE_LISTED_AT,
            source=SourceName.INTERNET_ARCHIVE,
            rows=[*_FIRST_PAGE_ROWS, *_SECOND_PAGE_ROWS],
        )
    ]


def test_an_sso_listing_is_listed_when_it_was_fetched() -> None:
    listing_page_rows = _build_listing_page_rows(2, SourceName.SSO, _SSO_FETCHED_AT)

    listings = get_listings(listing_page_rows)

    assert [listing.listed_at for listing in listings.listings] == [_SSO_FETCHED_AT]
    assert [listing.source for listing in listings.listings] == [SourceName.SSO]


def test_a_listing_missing_a_page_is_incomplete_and_gives_no_rows() -> None:
    first_run_without_page_one = _build_listing_page_rows(
        1, SourceName.INTERNET_ARCHIVE, _ARCHIVE_FETCHED_AT, page_indexes=(1,)
    )
    second_run_without_page_two = _build_listing_page_rows(
        2, SourceName.SSO, _SSO_FETCHED_AT, page_indexes=(0,)
    )

    listings = get_listings(first_run_without_page_one + second_run_without_page_two)

    assert listings.listings == []
    assert listings.incomplete_harvest_run_ids == [1, 2]


def test_a_page_with_no_text_or_no_result_count_is_left_out() -> None:
    listing_page_rows = [
        _build_listing_page_row(
            11, 1, SourceName.SSO, 0, "<html></html>", "", _SSO_FETCHED_AT
        ),
        _build_listing_page_row(12, 1, SourceName.SSO, 1, None, "", _SSO_FETCHED_AT),
    ]

    listings = get_listings(listing_page_rows)

    assert listings.listings == []
    assert listings.incomplete_harvest_run_ids == [1]


def test_an_archive_page_with_no_capture_time_raises() -> None:
    listing_page_row = ListingPageRow(
        id=1,
        requested_url=build_sso_listing_url(0),
        final_url=build_sso_listing_url(0),
        content_type=_LISTING_CONTENT_TYPE,
        body_text=_FIRST_PAGE_BODY.decode("utf-8"),
        fetched_at=_ARCHIVE_FETCHED_AT,
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
        listed_at=_SSO_FETCHED_AT,
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
            Listing(_SSO_FETCHED_AT, SourceName.SSO, [newer_row]),
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
    _seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, _ARCHIVE_FETCHED_AT)

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
    _seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, _ARCHIVE_FETCHED_AT)
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
    _seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, _ARCHIVE_FETCHED_AT)
    write_legislation(scratch_session, get_legislation_write(scratch_session))
    scratch_session.commit()
    _seed_listing(scratch_session, SourceName.SSO, _SSO_FETCHED_AT)

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
    _seed_listing(scratch_session, SourceName.INTERNET_ARCHIVE, _ARCHIVE_FETCHED_AT)
    write_legislation(scratch_session, get_legislation_write(scratch_session))
    scratch_session.commit()
    _seed_listing(scratch_session, SourceName.SSO, _SSO_FETCHED_AT, page_indexes=(0,))

    legislation_write = get_legislation_write(scratch_session)

    assert legislation_write.incomplete_harvest_run_ids == [2]
    assert legislation_write.legislation_updates == []
    assert legislation_write.unchanged_count == _CODE_COUNT
