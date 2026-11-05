from pathlib import Path

import pytest

from exceptions import OpenSgLawPdfTextError
from utils.pdf_text import PdfLine, PdfPage, get_pdf_pages, is_bold_font

_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures" / "pdf"
_INTERPRETATION_ACT_PAGE_COUNT = 2

_BOLD_FONT_NAMES = (
    "OEYWOQ+TimesNewRomanPS-BoldMT",
    "KHOMYX+TimesNewRomanPS-BoldItalicMT",
    "BLIEPA+AdvTT2cba4af3.B",
    "BLIFBE+AdvTT2cba4af3.B+20",
)
_NOT_BOLD_FONT_NAMES = (
    "LCWBRX+TimesNewRomanPSMT",
    "FWNFYH+TimesNewRomanPS-ItalicMT",
    "BLIEPB+AdvTT5843c571",
    "BLIEPC+AdvTTf90d833a.I",
    "BLIFAD+AdvTT5843c571+20",
    "BLIFCE+AdvTTf90d833a.I+20",
)


def _get_pages(file_name: str) -> list[PdfPage]:
    return get_pdf_pages((_FIXTURES_DIRECTORY / file_name).read_bytes())


def _get_line(page: PdfPage, text_start: str) -> PdfLine:
    return next(line for line in page.lines if line.text.startswith(text_start))


def test_the_interpretation_act_fixture_has_two_pages_numbered_from_one() -> None:
    pdf_pages = _get_pages("IA1965-p5-6.pdf")

    assert [pdf_page.page_number for pdf_page in pdf_pages] == [1, 2]
    assert len(pdf_pages) == _INTERPRETATION_ACT_PAGE_COUNT


def test_the_running_header_and_footer_are_margin_lines() -> None:
    pdf_page = _get_pages("IA1965-p5-6.pdf")[0]

    margin_texts = [line.text for line in pdf_page.lines if line.is_margin]

    assert any("Interpretation Act 1965" in text for text in margin_texts)
    assert any("version in force from 25/11/2024" in text for text in margin_texts)
    assert not _get_line(pdf_page, "PART 1").is_margin


def test_the_page_number_printed_just_above_the_footer_is_a_margin_line() -> None:
    pdf_page = _get_pages("AA1906-p3-4.pdf")[0]

    page_number_line = next(line for line in pdf_page.lines if line.text == "1")

    assert page_number_line.is_margin
    assert not _get_line(pdf_page, "[4/2021]").is_margin


def test_a_heading_line_is_bold() -> None:
    pdf_page = _get_pages("IA1965-p5-6.pdf")[0]

    heading_line = _get_line(pdf_page, "Interpretation of certain words")

    assert heading_line.is_bold
    assert heading_line.text == "Interpretation of certain words and expressions"


def test_a_section_line_has_a_bold_number_and_is_not_bold() -> None:
    pdf_page = _get_pages("IA1965-p5-6.pdf")[0]

    section_line = _get_line(pdf_page, "2.—(1) In this Act")

    assert section_line.bold_prefix == "2."
    assert not section_line.is_bold


def test_a_part_line_is_not_bold() -> None:
    pdf_page = _get_pages("IA1965-p5-6.pdf")[0]

    part_line = _get_line(pdf_page, "PART 1")

    assert not part_line.is_bold
    assert part_line.bold_prefix == ""


def test_a_fully_bold_line_has_its_whole_text_as_bold_prefix() -> None:
    pdf_page = _get_pages("IA1965-p5-6.pdf")[0]

    heading_line = _get_line(pdf_page, "Interpretation of certain words")

    assert heading_line.bold_prefix == heading_line.text


def test_a_justified_line_keeps_the_spaces_it_prints() -> None:
    pdf_page = _get_pages("IA1965-p5-6.pdf")[0]

    abet_line = _get_line(pdf_page, "“abet”")

    assert abet_line.text == (
        "“abet”, with its grammatical variations and cognate expressions,"
    )


def test_a_repealed_section_line_has_a_bold_number_in_the_advtt_font() -> None:
    pdf_page = _get_pages("AA1906-p3-4.pdf")[1]

    repealed_line = _get_line(pdf_page, "3. [Repealed by Act 25 of 2010]")

    assert repealed_line.bold_prefix == "3."
    assert not repealed_line.is_bold


@pytest.mark.parametrize("font_name", _BOLD_FONT_NAMES)
def test_a_bold_font_name_is_bold(font_name: str) -> None:
    assert is_bold_font(font_name)


@pytest.mark.parametrize("font_name", _NOT_BOLD_FONT_NAMES)
def test_a_font_name_that_is_not_bold_is_not_bold(font_name: str) -> None:
    assert not is_bold_font(font_name)


def test_a_body_that_is_not_a_pdf_raises() -> None:
    with pytest.raises(OpenSgLawPdfTextError, match="not a readable PDF"):
        get_pdf_pages(b"not a pdf")


def test_a_body_that_only_starts_like_a_pdf_raises() -> None:
    with pytest.raises(OpenSgLawPdfTextError, match="not a readable PDF"):
        get_pdf_pages(b"%PDF-")


@pytest.mark.parametrize("file_name", ("IA1965-p5-6.pdf", "AA1906-p3-4.pdf"))
def test_every_page_counts_its_images_as_a_whole_number(file_name: str) -> None:
    pdf_pages = _get_pages(file_name)

    assert all(pdf_page.image_count >= 0 for pdf_page in pdf_pages)
