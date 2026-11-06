from pathlib import Path

import pytest

from enums import LegislationSectionKind
from exceptions import OpenSgLawSectionParseError
from services.legislation_section import ParsedSection, get_parsed_legislation
from utils.pdf_text import PdfPage, get_pdf_pages

_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures" / "pdf"
_INTERPRETATION_ACT_CODE = "IA1965"
_CONSTITUTION_CODE = "CONS1963"
_APPRAISERS_ACT_CODE = "AA1906"
_SINGAPORE_TOURISM_BOARD_ACT_CODE = "STBA1963"
_GAMBLING_DUTIES_ACT_CODE = "GDA2022"
_GAMBLING_REGULATORY_AUTHORITY_ACT_CODE = "GRASA2022"
_ELECTRIC_VEHICLES_CHARGING_ACT_CODE = "EVCA2022"
_CONSUMER_PROTECTION_ACT_CODE = "CPFTA2003"
_CUSTOMS_ACT_CODE = "CA1960"
_LAW_ENFORCEMENT_ACT_CODE = "LEOMA2024"
_INTERPRETATION_ACT_FIXTURE_PAGE_COUNT = 2
_GAMBLING_DUTIES_ACT_FIXTURE_PAGE_COUNT = 3


def _get_pages(file_name: str) -> list[PdfPage]:
    return get_pdf_pages((_FIXTURES_DIRECTORY / file_name).read_bytes())


def _get_printed_numbers(parsed_sections: list[ParsedSection]) -> list[str]:
    return [parsed_section.printed_number for parsed_section in parsed_sections]


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

    assert _get_printed_numbers(parsed_legislation.sections) == ["47", "48"]
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
    printed_numbers = _get_printed_numbers(parsed_legislation.sections)
    amending_section = parsed_legislation.sections[1]

    assert printed_numbers == ["47", "48", "49"]
    assert "29.—(1) The Authority may establish a system" in amending_section.text
    assert "“Electronic service system" in amending_section.text
    assert amending_section.last_page_number == _GAMBLING_DUTIES_ACT_FIXTURE_PAGE_COUNT


def test_a_heading_whose_quoted_term_wraps_onto_a_second_line_stays_one_heading() -> (
    None
):
    pdf_pages = _get_pages("EVCA2022-p13.pdf")

    parsed_legislation = get_parsed_legislation(
        _ELECTRIC_VEHICLES_CHARGING_ACT_CODE, pdf_pages
    )
    supply_section, operator_section = parsed_legislation.sections

    assert supply_section.printed_number == "3"
    assert supply_section.text.endswith("(b) resale.")
    assert operator_section.printed_number == "4"
    assert operator_section.heading == (
        "Meanings of “charging station operator”, “electric vehicle"
        " charging service” and associated terms"
    )


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


def test_a_quotation_closed_by_a_modifier_letter_double_apostrophe_is_closed() -> None:
    pdf_pages = _get_pages("CPFTA2003-second-schedule.pdf")

    parsed_legislation = get_parsed_legislation(
        _CONSUMER_PROTECTION_ACT_CODE, pdf_pages
    )

    assert _get_printed_numbers(parsed_legislation.sections) == [
        "44",
        "FIRST SCHEDULE",
        "SECOND SCHEDULE",
    ]
    assert (
        "“This is not a bill. You are not required to pay any money.ˮ,"
        in parsed_legislation.sections[2].text
    )


def test_a_quotation_closed_by_two_right_single_quotes_is_closed() -> None:
    pdf_pages = _get_pages("LEOMA2024-p26-30.pdf")

    parsed_legislation = get_parsed_legislation(_LAW_ENFORCEMENT_ACT_CODE, pdf_pages)

    assert _get_printed_numbers(parsed_legislation.sections) == ["13", "14", "15"]
    assert "disorder, and take P’’; and" in parsed_legislation.sections[0].text


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

    assert _get_printed_numbers(parsed_legislation.sections) == ["1"]
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

    assert _get_printed_numbers(parsed_legislation.sections) == ["52", "53", "54", "55"]
    assert last_section.heading == "Act to bind Government"
    assert last_section.text == "55. This Act binds the Government."
    assert all(
        "LEGISLATIVE HISTORY" not in parsed_section.text
        and "Act XIV of 1867" not in parsed_section.text
        for parsed_section in parsed_legislation.sections
    )


def test_the_articles_of_the_constitution_are_kind_article() -> None:
    pdf_pages = _get_pages("CONS1963-p2-11.pdf")

    parsed_legislation = get_parsed_legislation(_CONSTITUTION_CODE, pdf_pages)

    assert _get_printed_numbers(parsed_legislation.sections) == ["1", "2"]
    assert all(
        parsed_section.kind == LegislationSectionKind.ARTICLE
        for parsed_section in parsed_legislation.sections
    )
    assert parsed_legislation.sections[0].heading == "Citation"
    assert parsed_legislation.sections[0].part_heading == "PART 1\nPRELIMINARY"


def test_an_article_printed_after_a_footnote_asterisk_starts_its_own_row() -> None:
    pdf_pages = _get_pages("CONS1963-article-3.pdf")

    parsed_legislation = get_parsed_legislation(_CONSTITUTION_CODE, pdf_pages)
    article_2, article_3 = parsed_legislation.sections[1:3]

    assert _get_printed_numbers(parsed_legislation.sections) == ["1", "2", "3", "4"]
    assert article_3.heading == "Republic of Singapore"
    assert article_3.sso_anchor == "#pr3-"
    assert article_3.text.startswith("*3. Singapore shall be a sovereign republic")
    assert "sovereign republic" not in article_2.text


def test_the_sections_of_an_act_stay_kind_section() -> None:
    pdf_pages = _get_pages("IA1965-p1-4.pdf")

    parsed_legislation = get_parsed_legislation(_INTERPRETATION_ACT_CODE, pdf_pages)

    assert all(
        parsed_section.kind == LegislationSectionKind.SECTION
        for parsed_section in parsed_legislation.sections
    )


def test_repealed_sections_are_flagged_and_their_neighbours_are_not() -> None:
    pdf_pages = _get_pages("AA1906-p3-4.pdf")

    parsed_legislation = get_parsed_legislation(_APPRAISERS_ACT_CODE, pdf_pages)
    printed_number_to_section = {
        parsed_section.printed_number: parsed_section
        for parsed_section in parsed_legislation.sections
    }

    assert printed_number_to_section["3"].is_repealed
    assert printed_number_to_section["3"].heading is None
    assert printed_number_to_section["5"].is_repealed
    assert printed_number_to_section["5"].heading is None
    assert not printed_number_to_section["2"].is_repealed
    assert not printed_number_to_section["4"].is_repealed
    assert not printed_number_to_section["6"].is_repealed


def test_a_repealed_range_printed_as_one_line_is_one_row_flagged_repealed() -> None:
    pdf_pages = _get_pages("CA1960-p58.pdf")

    parsed_legislation = get_parsed_legislation(_CUSTOMS_ACT_CODE, pdf_pages)

    assert _get_printed_numbers(parsed_legislation.sections) == ["69", "70", "78"]
    assert parsed_legislation.sections[1].text == (
        "70. to 77. [Repealed by Act 5 of 2015]"
    )
    assert parsed_legislation.sections[1].is_repealed
    assert not parsed_legislation.sections[0].is_repealed
    assert not parsed_legislation.sections[2].is_repealed


def test_the_schedule_of_an_act_is_one_row_of_kind_schedule() -> None:
    pdf_pages = _get_pages("AA1906-schedule.pdf")

    parsed_legislation = get_parsed_legislation(_APPRAISERS_ACT_CODE, pdf_pages)
    schedule_sections = [
        parsed_section
        for parsed_section in parsed_legislation.sections
        if parsed_section.kind == LegislationSectionKind.SCHEDULE
    ]

    assert _get_printed_numbers(schedule_sections) == ["THE SCHEDULE"]
    assert schedule_sections[0].heading is None
    assert schedule_sections[0].part_heading is None
    assert not schedule_sections[0].is_repealed
    assert parsed_legislation.sections[-1] == schedule_sections[0]
    assert "APPRAISER’S LICENCE" in schedule_sections[0].text
    assert [
        parsed_section.is_repealed for parsed_section in parsed_legislation.sections
    ] == [True, True, False, False, False, False, False]


def test_the_numbered_paragraphs_of_a_schedule_start_no_section() -> None:
    pdf_pages = _get_pages("CONS1963-first-schedule.pdf")

    parsed_legislation = get_parsed_legislation(_CONSTITUTION_CODE, pdf_pages)
    printed_numbers = _get_printed_numbers(parsed_legislation.sections)
    first_schedule = parsed_legislation.sections[-1]

    assert printed_numbers == ["1", "2", "FIRST SCHEDULE"]
    assert first_schedule.kind == LegislationSectionKind.SCHEDULE
    assert "1. Oath of Office of President" in first_schedule.text
    assert "1A. Oath of Office of Person Exercising Functions" in first_schedule.text
    assert "4A. Oath for due execution of Office of Minister" in first_schedule.text
    assert parsed_legislation.sections[0].first_page_number == 1


def test_a_schedule_heading_printed_again_at_a_page_top_is_dropped() -> None:
    pdf_pages = _get_pages("CONS1963-first-schedule.pdf")

    first_schedule = get_parsed_legislation(_CONSTITUTION_CODE, pdf_pages).sections[-1]

    assert "continued" not in first_schedule.text
    assert first_schedule.last_page_number == len(pdf_pages)


def test_a_schedule_label_printed_twice_raises() -> None:
    pdf_pages = _get_pages("AA1906-schedule.pdf")

    with pytest.raises(
        OpenSgLawSectionParseError, match="AA1906 prints section THE SCHEDULE twice"
    ):
        get_parsed_legislation(_APPRAISERS_ACT_CODE, pdf_pages + pdf_pages)


def test_a_section_on_a_page_with_an_image_is_flagged() -> None:
    pdf_pages = _get_pages("STBA1963-image.pdf")

    parsed_legislation = get_parsed_legislation(
        _SINGAPORE_TOURISM_BOARD_ACT_CODE, pdf_pages
    )
    winding_up_section = parsed_legislation.sections[0]

    assert pdf_pages[0].image_count > 0
    assert winding_up_section.printed_number == "46"
    assert winding_up_section.is_on_image_page
    assert winding_up_section.sso_anchor == "#pr46-"


def test_a_schedule_has_no_sso_anchor() -> None:
    pdf_pages = _get_pages("STBA1963-image.pdf")

    schedule = get_parsed_legislation(
        _SINGAPORE_TOURISM_BOARD_ACT_CODE, pdf_pages
    ).sections[-1]

    assert schedule.kind == LegislationSectionKind.SCHEDULE
    assert schedule.sso_anchor is None
    assert schedule.is_on_image_page


def test_the_sections_of_pages_without_an_image_are_not_flagged() -> None:
    pdf_pages = _get_pages("IA1965-p5-6.pdf")

    parsed_legislation = get_parsed_legislation(_INTERPRETATION_ACT_CODE, pdf_pages)

    assert all(pdf_page.image_count == 0 for pdf_page in pdf_pages)
    assert not any(
        parsed_section.is_on_image_page
        for parsed_section in parsed_legislation.sections
    )
    assert parsed_legislation.sections[0].printed_number == "2"
    assert parsed_legislation.sections[0].sso_anchor == "#pr2-"
