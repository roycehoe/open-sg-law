import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from crud.legislation_section import CRUDLegislationSection, LegislationSectionRow
from crud.legislation_version import CRUDLegislationVersion
from database.legislation_section import LegislationSection
from database.legislation_version import LegislationVersion
from enums import LegislationSectionKind
from tests.legislation_version_seed import build_version, seed_version_inputs


def _seed_version(session: Session) -> int:
    CRUDLegislationVersion(session).add_many(
        [build_version(seed_version_inputs(session))]
    )
    legislation_version_id = session.exec(select(LegislationVersion.id)).one()
    assert legislation_version_id is not None
    return legislation_version_id


def _build_section(
    legislation_version_id: int, ordinal: int, printed_number: str
) -> LegislationSection:
    return LegislationSection(
        ordinal=ordinal,
        printed_number=printed_number,
        heading="Short title",
        part_heading="PART 1\nPRELIMINARY",
        text=f"{printed_number}. This Act is the Interpretation Act 1965.",
        first_page_number=1,
        last_page_number=2,
        sso_anchor=f"#pr{printed_number}-",
        kind=LegislationSectionKind.SECTION,
        is_repealed=False,
        is_on_image_page=False,
        legislation_version_id=legislation_version_id,
    )


def test_sections_are_read_back_in_ordinal_order(scratch_session: Session) -> None:
    legislation_version_id = _seed_version(scratch_session)

    CRUDLegislationSection(scratch_session).add_many(
        [
            _build_section(legislation_version_id, 2, "2"),
            _build_section(legislation_version_id, 1, "1"),
        ]
    )
    legislation_section_rows = CRUDLegislationSection(
        scratch_session
    ).get_rows_by_legislation_version_id(legislation_version_id)

    assert CRUDLegislationSection(scratch_session).get_count() == len(
        legislation_section_rows
    )
    assert legislation_section_rows == [
        LegislationSectionRow(
            ordinal=ordinal,
            printed_number=str(ordinal),
            heading="Short title",
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
        [_build_section(legislation_version_id, 1, "1")]
    )

    CRUDLegislationSection(scratch_session).delete_by_legislation_version_id(
        legislation_version_id
    )

    assert CRUDLegislationSection(scratch_session).get_count() == 0
    assert (
        CRUDLegislationSection(scratch_session).get_count_by_legislation_version_id(
            legislation_version_id
        )
        == 0
    )


def test_a_second_section_with_one_ordinal_is_refused(scratch_session: Session) -> None:
    legislation_version_id = _seed_version(scratch_session)
    CRUDLegislationSection(scratch_session).add_many(
        [_build_section(legislation_version_id, 1, "1")]
    )

    with pytest.raises(IntegrityError):
        CRUDLegislationSection(scratch_session).add_many(
            [_build_section(legislation_version_id, 1, "2")]
        )


def test_a_kind_outside_the_enum_is_refused(scratch_session: Session) -> None:
    legislation_version_id = _seed_version(scratch_session)
    legislation_section = _build_section(legislation_version_id, 1, "1")
    legislation_section.kind = "CLAUSE"  # pyright: ignore[reportAttributeAccessIssue] the test stores a value outside the enum to reach the check constraint

    with pytest.raises(IntegrityError):
        CRUDLegislationSection(scratch_session).add_many([legislation_section])
