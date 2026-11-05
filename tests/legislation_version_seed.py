from datetime import date, datetime, timezone

from sqlmodel import Session, select

from crud.harvest_run import CRUDHarvestRun
from crud.legislation import CRUDLegislation
from crud.source_response import CRUDSourceResponse
from database.harvest_run import HarvestRun
from database.legislation import Legislation
from database.legislation_section import LegislationSection
from database.legislation_version import LegislationVersion
from database.source_response import SourceResponse
from enums import LegislationSectionKind, ResponseKind, SourceName
from tests.source_seed import seed_sources

CAPTURED_AT = datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)
VERSION_DATE = date(2024, 11, 25)


def seed_version_inputs(session: Session) -> int:
    seed_sources(session)
    harvest_run = HarvestRun(source=SourceName.SSO)
    CRUDHarvestRun(session).create(harvest_run)
    assert harvest_run.id is not None
    CRUDSourceResponse(session).insert_on_conflict_do_nothing(
        SourceResponse(
            requested_url="https://sso.agc.gov.sg/Act/IA1965",
            final_url="https://sso.agc.gov.sg/Act/IA1965",
            status_code=200,
            body_bytes=b"%PDF-",
            sha256="a" * 64,
            byte_length=5,
            kind=ResponseKind.DOCUMENT,
            source=SourceName.SSO,
            harvest_run_id=harvest_run.id,
        )
    )
    CRUDLegislation(session).add_many(
        [
            Legislation(
                sso_code="IA1965",
                title="Interpretation Act 1965",
                is_in_newest_listing=True,
                listing_source=SourceName.SSO,
            )
        ]
    )
    session.commit()
    source_response_id = session.exec(select(SourceResponse.id)).one()
    assert source_response_id is not None
    return source_response_id


def build_version(source_response_id: int) -> LegislationVersion:
    return LegislationVersion(
        printed_version_date="25/11/2024",
        version_date=VERSION_DATE,
        captured_at=CAPTURED_AT,
        is_newest=False,
        source=SourceName.SSO,
        legislation_id=1,
        source_response_id=source_response_id,
    )


def build_section(
    legislation_version_id: int,
    ordinal: int,
    printed_number: str,
    heading: str,
    section_text: str,
) -> LegislationSection:
    return LegislationSection(
        ordinal=ordinal,
        printed_number=printed_number,
        heading=heading,
        part_heading="PART 1\nPRELIMINARY",
        text=section_text,
        first_page_number=1,
        last_page_number=2,
        sso_anchor=f"#pr{printed_number}-",
        kind=LegislationSectionKind.SECTION,
        is_repealed=False,
        is_on_image_page=False,
        legislation_version_id=legislation_version_id,
    )
