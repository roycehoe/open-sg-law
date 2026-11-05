from pathlib import Path

import pytest

from enums import LegislationSectionKind
from exceptions import OpenSgLawSectionParseError
from services.legislation_section import get_parsed_legislation
from utils.pdf_text import PdfPage, get_pdf_pages

_FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "pdf"
_INTERPRETATION_ACT_CODE = "IA1965"
_GAMBLING_DUTIES_ACT_CODE = "GDA2022"
_GAMBLING_REGULATORY_AUTHORITY_ACT_CODE = "GRASA2022"
_INTERPRETATION_ACT_FIXTURE_PAGE_COUNT = 2
_GAMBLING_DUTIES_ACT_FIXTURE_PAGE_COUNT = 3


def _get_pages(file_name: str) -> list[PdfPage]:
    return get_pdf_pages((_FIXTURE_DIRECTORY / file_name).read_bytes())


def test_the_first_section_of_the_interpretation_act_carries_its_part_and_heading() -> (
    None
):
    pdf_pages = _get_pages("IA1965-p5-6.pdf")

    parsed_legislation = get_parsed_legislation(_INTERPRETATION_ACT_CODE, pdf_pages)
    first_section = parsed_legislation.sections[0]

    assert first_section.ordinal == 1
    assert first_section.printed_number == "2"
    assert first_section.heading == "Interpretation of certain words and expressions"
    assert first_section.part_heading == "PART 1\nGENERAL PROVISIONS OF INTERPRETATION"
    assert first_section.division_heading is None
    assert first_section.text.startswith(
        "2.—(1) In this Act, and in every written law enacted before, on or"
    )
    assert first_section.kind == LegislationSectionKind.SECTION
    assert first_section.first_page_number == 1
    assert first_section.last_page_number == _INTERPRETATION_ACT_FIXTURE_PAGE_COUNT


def test_the_running_header_and_footer_stay_out_of_the_section_text() -> None:
    pdf_pages = _get_pages("IA1965-p5-6.pdf")

    first_section = get_parsed_legislation(
        _INTERPRETATION_ACT_CODE, pdf_pages
    ).sections[0]

    assert "Informal Consolidation" not in first_section.text
    assert "NO. " not in first_section.text
    assert "Interpretation Act 1965" not in first_section.text


def test_the_body_holds_at_least_the_characters_that_landed_in_a_section() -> None:
    pdf_pages = _get_pages("IA1965-p5-6.pdf")

    parsed_legislation = get_parsed_legislation(_INTERPRETATION_ACT_CODE, pdf_pages)

    assert (
        parsed_legislation.body_character_count
        >= parsed_legislation.section_character_count
        > 0
    )


def test_a_section_quoted_by_an_amending_section_stays_in_its_text() -> None:
    pdf_pages = _get_pages("GRASA2022-p34-37.pdf")

    parsed_legislation = get_parsed_legislation(
        _GAMBLING_REGULATORY_AUTHORITY_ACT_CODE, pdf_pages
    )
    amending_section = parsed_legislation.sections[1]

    assert [
        parsed_section.printed_number for parsed_section in parsed_legislation.sections
    ] == ["47", "48"]
    assert amending_section.printed_number == "48"
    assert "Authorised persons" in amending_section.text
    assert "5. It is the function of the Authority" in amending_section.text
    assert "7.—(1) The Authority may in writing appoint" in amending_section.text
    assert amending_section.part_heading is not None
    assert amending_section.part_heading.startswith("PART 8\n")
    assert amending_section.heading == "Amendment of Casino Control Act 2006"


def test_a_section_quoted_across_pages_stays_in_the_amending_section() -> None:
    pdf_pages = _get_pages("GDA2022-p56-57-61.pdf")

    parsed_legislation = get_parsed_legislation(_GAMBLING_DUTIES_ACT_CODE, pdf_pages)
    printed_numbers = [
        parsed_section.printed_number for parsed_section in parsed_legislation.sections
    ]
    amending_section = parsed_legislation.sections[1]

    assert printed_numbers == ["47", "48", "49"]
    assert "29.—(1) The Authority may establish a system" in amending_section.text
    assert "“Electronic service system" in amending_section.text
    assert amending_section.last_page_number == _GAMBLING_DUTIES_ACT_FIXTURE_PAGE_COUNT


def test_a_quoted_line_with_a_closing_quote_before_any_opening_one_starts_nothing() -> (
    None
):
    pdf_pages = _get_pages("GDA2022-p56-57-61.pdf")

    parsed_legislation = get_parsed_legislation(_GAMBLING_DUTIES_ACT_CODE, pdf_pages)

    assert parsed_legislation.sections[0].printed_number == "47"
    assert parsed_legislation.sections[0].heading == (
        "Consequential amendments to Goods and Services Tax Act"
    )
    assert parsed_legislation.sections[1].heading == (
        "Consequential amendments to Inland Revenue Authority of Singapore Act"
    )


def test_two_copies_of_the_same_pages_print_a_section_twice() -> None:
    pdf_pages = _get_pages("IA1965-p5-6.pdf")

    with pytest.raises(
        OpenSgLawSectionParseError, match="IA1965 prints section 2 twice"
    ):
        get_parsed_legislation(_INTERPRETATION_ACT_CODE, pdf_pages + pdf_pages)


def test_a_page_that_opens_a_quotation_and_never_closes_it_raises() -> None:
    pdf_pages = _get_pages("GRASA2022-p34-37.pdf")

    with pytest.raises(
        OpenSgLawSectionParseError, match="GRASA2022 leaves a quotation open"
    ):
        get_parsed_legislation(_GAMBLING_REGULATORY_AUTHORITY_ACT_CODE, pdf_pages[2:3])


def test_a_page_with_no_section_start_raises() -> None:
    pdf_pages = _get_pages("IA1965-p5-6.pdf")

    with pytest.raises(OpenSgLawSectionParseError, match="IA1965 prints no section"):
        get_parsed_legislation(_INTERPRETATION_ACT_CODE, pdf_pages[1:2])


def test_the_arrangement_list_and_cover_are_front_matter_and_start_no_section() -> None:
    pdf_pages = _get_pages("IA1965-p1-4.pdf")

    parsed_legislation = get_parsed_legislation(_INTERPRETATION_ACT_CODE, pdf_pages)
    first_section = parsed_legislation.sections[0]

    assert [
        parsed_section.printed_number for parsed_section in parsed_legislation.sections
    ] == ["1"]
    assert first_section.heading == "Short title"
    assert first_section.part_heading is None
    assert first_section.division_heading is None
    assert first_section.text == "1. This Act is the Interpretation Act 1965."


def test_the_front_matter_characters_are_left_out_of_the_body_count() -> None:
    pdf_pages = _get_pages("IA1965-p1-4.pdf")

    parsed_legislation = get_parsed_legislation(_INTERPRETATION_ACT_CODE, pdf_pages)
    first_section = parsed_legislation.sections[0]
    heading_and_text_length = len("Short title") + len(first_section.text)

    assert parsed_legislation.body_character_count == heading_and_text_length
    assert parsed_legislation.section_character_count == heading_and_text_length


def test_the_legislative_history_is_left_out_of_every_section() -> None:
    pdf_pages = _get_pages("IA1965-history.pdf")

    parsed_legislation = get_parsed_legislation(_INTERPRETATION_ACT_CODE, pdf_pages)
    last_section = parsed_legislation.sections[-1]

    assert [
        parsed_section.printed_number for parsed_section in parsed_legislation.sections
    ] == ["52", "53", "54", "55"]
    assert last_section.heading == "Act to bind Government"
    assert last_section.text == "55. This Act binds the Government."
    assert all(
        "LEGISLATIVE HISTORY" not in parsed_section.text
        and "Act XIV of 1867" not in parsed_section.text
        for parsed_section in parsed_legislation.sections
    )
