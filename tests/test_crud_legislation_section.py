import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from crud.legislation_section import CRUDLegislationSection, LegislationSectionRow
from crud.legislation_version import CRUDLegislationVersion
from database.legislation_version import LegislationVersion
from database.source_response import SourceResponse
from enums import LegislationSectionKind, SourceName
from tests.document_seed import (
    IA1965_BODY,
    IA1965_OTHER_SSO_URL,
    SSO_FETCHED_AT,
    seed_document,
    seed_harvest_run,
)
from tests.legislation_version_seed import (
    build_section,
    build_version,
    seed_version_inputs,
)

_SHORT_TITLE_HEADING = "Short title"


def _seed_version(session: Session) -> int:
    CRUDLegislationVersion(session).add_many(
        [build_version(seed_version_inputs(session))]
    )
    legislation_version_id = session.exec(select(LegislationVersion.id)).one()
    assert legislation_version_id is not None
    return legislation_version_id


def _seed_other_version(session: Session) -> int:
    seed_document(
        session,
        seed_harvest_run(session, SourceName.SSO),
        SourceName.SSO,
        IA1965_OTHER_SSO_URL,
        IA1965_BODY,
        SSO_FETCHED_AT,
    )
    source_response_id = session.exec(
        select(SourceResponse.id).where(
            SourceResponse.requested_url == IA1965_OTHER_SSO_URL
        )
    ).one()
    assert source_response_id is not None
    CRUDLegislationVersion(session).add_many([build_version(source_response_id)])
    legislation_version_id = session.exec(
        select(LegislationVersion.id).where(
            LegislationVersion.source_response_id == source_response_id
        )
    ).one()
    assert legislation_version_id is not None
    return legislation_version_id


def test_sections_are_read_back_in_ordinal_order(scratch_session: Session) -> None:
    legislation_version_id = _seed_version(scratch_session)

    CRUDLegislationSection(scratch_session).add_many(
        [
            build_section(
                legislation_version_id,
                2,
                "2",
                _SHORT_TITLE_HEADING,
                "2. This Act is the Interpretation Act 1965.",
            ),
            build_section(
                legislation_version_id,
                1,
                "1",
                _SHORT_TITLE_HEADING,
                "1. This Act is the Interpretation Act 1965.",
            ),
        ]
    )
    legislation_section_rows = CRUDLegislationSection(
        scratch_session
    ).get_rows_by_legislation_version_id(legislation_version_id)

    assert legislation_section_rows == [
        LegislationSectionRow(
            ordinal=ordinal,
            printed_number=str(ordinal),
            heading=_SHORT_TITLE_HEADING,
            part_heading="PART 1\nPRELIMINARY",
            division_heading=None,
            text=f"{ordinal}. This Act is the Interpretation Act 1965.",
            first_page_number=1,
            last_page_number=2,
            sso_anchor=f"#pr{ordinal}-",
            kind=LegislationSectionKind.SECTION,
            is_repealed=False,
            is_on_image_page=False,
        )
        for ordinal in (1, 2)
    ]
    assert CRUDLegislationSection(scratch_session).get_count_by_legislation_version_id(
        legislation_version_id
    ) == len(legislation_section_rows)


def test_deleting_a_versions_sections_leaves_none(scratch_session: Session) -> None:
    legislation_version_id = _seed_version(scratch_session)
    CRUDLegislationSection(scratch_session).add_many(
        [
            build_section(
                legislation_version_id,
                1,
                "1",
                _SHORT_TITLE_HEADING,
                "1. This Act is the Interpretation Act 1965.",
            )
        ]
    )

    CRUDLegislationSection(scratch_session).delete_by_legislation_version_id(
        legislation_version_id
    )

    assert (
        CRUDLegislationSection(scratch_session).get_count_by_legislation_version_id(
            legislation_version_id
        )
        == 0
    )


def test_a_second_section_with_one_ordinal_is_refused(scratch_session: Session) -> None:
    legislation_version_id = _seed_version(scratch_session)
    CRUDLegislationSection(scratch_session).add_many(
        [
            build_section(
                legislation_version_id,
                1,
                "1",
                _SHORT_TITLE_HEADING,
                "1. This Act is the Interpretation Act 1965.",
            )
        ]
    )

    with pytest.raises(IntegrityError):
        CRUDLegislationSection(scratch_session).add_many(
            [
                build_section(
                    legislation_version_id,
                    1,
                    "2",
                    _SHORT_TITLE_HEADING,
                    "2. This Act is the Interpretation Act 1965.",
                )
            ]
        )


def test_a_kind_outside_the_enum_is_refused(scratch_session: Session) -> None:
    legislation_version_id = _seed_version(scratch_session)
    legislation_section = build_section(
        legislation_version_id,
        1,
        "1",
        _SHORT_TITLE_HEADING,
        "1. This Act is the Interpretation Act 1965.",
    )
    legislation_section.kind = "CLAUSE"  # pyright: ignore[reportAttributeAccessIssue] the test stores a value outside the enum to reach the check constraint

    with pytest.raises(IntegrityError):
        CRUDLegislationSection(scratch_session).add_many([legislation_section])


def test_a_second_section_with_one_printed_number_is_refused(
    scratch_session: Session,
) -> None:
    legislation_version_id = _seed_version(scratch_session)
    CRUDLegislationSection(scratch_session).add_many(
        [
            build_section(
                legislation_version_id,
                1,
                "9A",
                _SHORT_TITLE_HEADING,
                "9A. This Act is the Interpretation Act 1965.",
            )
        ]
    )

    with pytest.raises(IntegrityError):
        CRUDLegislationSection(scratch_session).add_many(
            [
                build_section(
                    legislation_version_id,
                    2,
                    "9A",
                    _SHORT_TITLE_HEADING,
                    "9A. This Act is the Interpretation Act 1965.",
                )
            ]
        )


def test_one_printed_number_is_kept_in_two_versions(scratch_session: Session) -> None:
    legislation_version_id = _seed_version(scratch_session)
    other_legislation_version_id = _seed_other_version(scratch_session)

    CRUDLegislationSection(scratch_session).add_many(
        [
            build_section(
                legislation_version_id,
                1,
                "9A",
                _SHORT_TITLE_HEADING,
                "9A. This Act is the Interpretation Act 1965.",
            ),
            build_section(
                other_legislation_version_id,
                1,
                "9A",
                _SHORT_TITLE_HEADING,
                "9A. This Act is the Interpretation Act 1965.",
            ),
        ]
    )

    assert (
        CRUDLegislationSection(scratch_session).get_count_by_legislation_version_id(
            other_legislation_version_id
        )
        == 1
    )
