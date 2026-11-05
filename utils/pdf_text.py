import io
import re
from dataclasses import dataclass
from typing import cast

import pdfplumber
from pdfplumber.page import Page
from pdfplumber.utils.exceptions import PdfminerException

from exceptions import OpenSgLawPdfTextError

_SUBSET_PREFIX_PATTERN = re.compile(r"^[A-Z]{6}\+")
_BOLD_FONT_PATTERN = re.compile(r"Bold|^AdvTT[0-9a-f]+\.BI?(\+[0-9a-f]+)?$")
_HEADER_BOTTOM_POINTS = 66
_FOOTER_TOP_POINTS = 650
_X_TOLERANCE_POINTS = 1.5


@dataclass(frozen=True)
class PdfLine:
    text: str
    bold_prefix: str
    top: float
    is_bold: bool
    is_margin: bool


@dataclass(frozen=True)
class PdfPage:
    page_number: int
    lines: list[PdfLine]
    image_count: int


def _is_bold_font(font_name: str) -> bool:
    return (
        _BOLD_FONT_PATTERN.search(_SUBSET_PREFIX_PATTERN.sub("", font_name)) is not None
    )


def _get_bold_prefix(text: str, chars: list[dict[str, object]]) -> str:
    bold_character_count = 0
    for char in chars:
        if not _is_bold_font(str(char["fontname"])):
            break
        bold_character_count += len(str(char["text"]))

    printed_character_count = 0
    for index, text_character in enumerate(text):
        if printed_character_count == bold_character_count:
            return text[:index].strip()
        if not text_character.isspace():
            printed_character_count += 1
    return text.strip()


def _build_pdf_line(text_line: dict[str, object]) -> PdfLine:
    text = str(text_line["text"])
    top = float(str(text_line["top"]))
    chars = [
        char
        for char in cast(list[dict[str, object]], text_line["chars"])
        if not str(char["text"]).isspace()
    ]
    return PdfLine(
        text=text,
        bold_prefix=_get_bold_prefix(text, chars),
        top=top,
        is_bold=all(_is_bold_font(str(char["fontname"])) for char in chars),
        is_margin=top < _HEADER_BOTTOM_POINTS or top > _FOOTER_TOP_POINTS,
    )


def _build_pdf_page(page: Page) -> PdfPage:
    text_lines = page.extract_text_lines(
        return_chars=True, strip=True, x_tolerance=_X_TOLERANCE_POINTS
    )
    return PdfPage(
        page_number=page.page_number,
        lines=[_build_pdf_line(text_line) for text_line in text_lines],
        image_count=len(page.images),
    )


def get_pdf_pages(pdf_bytes: bytes) -> list[PdfPage]:
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            return [_build_pdf_page(page) for page in pdf.pages]
    except PdfminerException as error:
        raise OpenSgLawPdfTextError("The body is not a readable PDF") from error
