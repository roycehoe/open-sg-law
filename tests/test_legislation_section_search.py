from sqlalchemy import func
from sqlmodel import Session, col, select

from crud.legislation_section import CRUDLegislationSection
from crud.legislation_version import CRUDLegislationVersion
from database.legislation_section import LegislationSection
from database.legislation_version import LegislationVersion
from enums import LegislationSectionKind
from tests.legislation_version_seed import build_version, seed_version_inputs

_PURPOSIVE_HEADING = (
    "Purposive interpretation of written law and use of extrinsic\nmaterials"
)
_PURPOSIVE_TEXT = (
    "9A.—(1) In the interpretation of a provision of a written law, an\n"
    "interpretation that would promote the purpose or object underlying\n"
    "the written law (whether that purpose or object is expressly stated in\n"
    "the written law or not) is to be preferred to an interpretation that\n"
    "would not promote that purpose or object."
)
_STYLE_HEADING = "Changes to style not to affect meaning"
_STYLE_TEXT = (
    "9B. Where —\n"
    "(a) a provision of an Act has expressed an idea in a particular\n"
    "form of words; and\n"
    "(b) a revised edition or a later provision of that Act, or a later\n"
    "Act, appears to have expressed the same idea in a different\n"
    "form of words for the purpose of using a clearer style,\n"
    "the ideas are not to be taken to be different merely because different\n"
    "forms of words were used."
)


def _build_section(
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
        text=section_text,
        first_page_number=1,
        last_page_number=1,
        sso_anchor=f"#pr{printed_number}-",
        kind=LegislationSectionKind.SECTION,
        is_repealed=False,
        is_on_image_page=False,
        legislation_version_id=legislation_version_id,
    )


def test_a_keyword_finds_only_the_section_that_holds_it(
    scratch_session: Session,
) -> None:
    CRUDLegislationVersion(scratch_session).add_many(
        [build_version(seed_version_inputs(scratch_session))]
    )
    legislation_version_id = scratch_session.exec(select(LegislationVersion.id)).one()
    assert legislation_version_id is not None
    CRUDLegislationSection(scratch_session).add_many(
        [
            _build_section(
                legislation_version_id, 1, "9A", _PURPOSIVE_HEADING, _PURPOSIVE_TEXT
            ),
            _build_section(
                legislation_version_id, 2, "9B", _STYLE_HEADING, _STYLE_TEXT
            ),
        ]
    )

    statement = select(LegislationSection.printed_number).where(
        col(LegislationSection.search_vector).op("@@")(
            func.plainto_tsquery("english", "interpret")
        )
    )

    assert scratch_session.exec(statement).all() == ["9A"]
