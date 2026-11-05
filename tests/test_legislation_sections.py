from sqlmodel import Session, select, update

from crud.legislation_section import CRUDLegislationSection
from crud.legislation_version import CRUDLegislationVersion, VersionDocumentRow
from database.legislation_section import LegislationSection
from database.legislation_version import LegislationVersion
from enums import LegislationSectionKind
from populate.legislation_sections import get_version_sections, write_version_sections
from tests.document_seed import seed_ia1965_version

_BODY_CHARACTER_COUNT = 2960
_SECTION_CHARACTER_COUNT = 2960
_EDITED_TEXT = "2. edited"


def _get_version_document_row(session: Session) -> VersionDocumentRow:
    return CRUDLegislationVersion(session).get_version_document_rows()[0]


def test_the_version_document_row_joins_the_act_code(scratch_session: Session) -> None:
    legislation_version_id = seed_ia1965_version(scratch_session)

    version_document_row = _get_version_document_row(scratch_session)

    assert version_document_row.id == legislation_version_id
    assert version_document_row.sso_code == "IA1965"


def test_the_write_stores_the_sections_and_both_character_counts(
    scratch_session: Session,
) -> None:
    legislation_version_id = seed_ia1965_version(scratch_session)

    version_sections = get_version_sections(
        scratch_session, _get_version_document_row(scratch_session)
    )
    write_version_sections(scratch_session, version_sections)

    assert version_sections.is_changed is True
    legislation_section_rows = CRUDLegislationSection(
        scratch_session
    ).get_rows_by_legislation_version_id(legislation_version_id)
    assert [
        (legislation_section_row.printed_number, legislation_section_row.kind)
        for legislation_section_row in legislation_section_rows
    ] == [("2", LegislationSectionKind.SECTION)]
    scratch_session.expire_all()
    legislation_version = scratch_session.exec(select(LegislationVersion)).one()
    assert legislation_version.body_character_count == _BODY_CHARACTER_COUNT
    assert legislation_version.section_character_count == _SECTION_CHARACTER_COUNT


def test_a_second_read_finds_the_stored_sections_unchanged(
    scratch_session: Session,
) -> None:
    seed_ia1965_version(scratch_session)
    write_version_sections(
        scratch_session,
        get_version_sections(
            scratch_session, _get_version_document_row(scratch_session)
        ),
    )
    section_id_before = scratch_session.exec(select(LegislationSection.id)).one()

    version_sections = get_version_sections(
        scratch_session, _get_version_document_row(scratch_session)
    )
    write_version_sections(scratch_session, version_sections)

    assert version_sections.is_changed is False
    assert (
        scratch_session.exec(select(LegislationSection.id)).one() == section_id_before
    )


def test_a_stored_section_that_differs_from_the_parse_is_rewritten(
    scratch_session: Session,
) -> None:
    legislation_version_id = seed_ia1965_version(scratch_session)
    write_version_sections(
        scratch_session,
        get_version_sections(
            scratch_session, _get_version_document_row(scratch_session)
        ),
    )
    scratch_session.execute(update(LegislationSection).values(text=_EDITED_TEXT))

    version_sections = get_version_sections(
        scratch_session, _get_version_document_row(scratch_session)
    )
    write_version_sections(scratch_session, version_sections)

    assert version_sections.is_changed is True
    (legislation_section_row,) = CRUDLegislationSection(
        scratch_session
    ).get_rows_by_legislation_version_id(legislation_version_id)
    assert legislation_section_row.text != _EDITED_TEXT
    assert legislation_section_row.text.startswith("2.—(1) In this Act")
