from datetime import date, datetime, timezone

from database.legislation_section import LegislationSection
from database.legislation_version import LegislationVersion
from enums import LegislationSectionKind, SourceName

CAPTURED_AT = datetime(2026, 11, 5, 9, 0, tzinfo=timezone.utc)
VERSION_DATE = date(2024, 11, 25)


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
