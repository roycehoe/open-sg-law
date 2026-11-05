import re
from dataclasses import dataclass
from typing import Optional

from enums import LegislationSectionKind
from exceptions import OpenSgLawSectionParseError
from utils.pdf_text import PdfLine, PdfPage

_SECTION_NUMBER_PATTERN = re.compile(r"^(\d+[A-Z]*)\.")
_PART_PATTERN = re.compile(r"^PART \d+[A-Z]*$")
_DIVISION_PATTERN = re.compile(r"^Division \d+[A-Z]* — ")
_OPENING_QUOTE = "“"
_CLOSING_QUOTE = "”"
_BODY_END_LINES = frozenset({"LEGISLATIVE HISTORY", "COMPARATIVE TABLE"})
_CONTINUED_SUFFIX = "— continued"


@dataclass(frozen=True)
class ParsedSection:
    ordinal: int
    printed_number: str
    heading: Optional[str]
    part_heading: Optional[str]
    division_heading: Optional[str]
    text: str
    first_page_number: int
    last_page_number: int
    kind: LegislationSectionKind


@dataclass(frozen=True)
class ParsedLegislation:
    sections: list[ParsedSection]
    body_character_count: int
    section_character_count: int


@dataclass(frozen=True)
class _HeldLine:
    text: str
    page_number: int
    line_index: int


@dataclass
class _OpenSection:
    printed_number: str
    heading: Optional[str]
    part_heading: Optional[str]
    division_heading: Optional[str]
    text_lines: list[str]
    first_page_number: int
    last_page_number: int


class _SectionWalk:
    def __init__(self, sso_code: str):
        self.sso_code: str = sso_code
        self.sections: list[_OpenSection] = []
        self.printed_numbers: set[str] = set()
        self.line_lengths: list[int] = []
        self.kept_line_indices: set[int] = set()
        self.held_headings: list[_HeldLine] = []
        self.quote_depth: int = 0
        self.part_heading: Optional[str] = None
        self.part_first_line_index: Optional[int] = None
        self.is_reading_part_title: bool = False
        self.division_heading: Optional[str] = None
        self.division_line_index: Optional[int] = None
        self.body_first_line_index: Optional[int] = None
        self.is_body_over: bool = False

    def _add_to_section_text(
        self, text: str, page_number: int, line_index: int
    ) -> None:
        if not self.sections:
            return
        current_section = self.sections[-1]
        current_section.text_lines.append(text)
        current_section.last_page_number = page_number
        self.kept_line_indices.add(line_index)

    def _clear_part_and_division(self) -> None:
        self.part_heading = None
        self.part_first_line_index = None
        self.is_reading_part_title = False
        self.division_heading = None
        self.division_line_index = None

    def _flush_held_headings(self) -> None:
        for held_heading in self.held_headings:
            self._add_to_section_text(
                held_heading.text, held_heading.page_number, held_heading.line_index
            )
        self.held_headings = []

    def _start_section(
        self, printed_number: str, line: PdfLine, page_number: int, line_index: int
    ) -> None:
        if printed_number in self.printed_numbers:
            raise OpenSgLawSectionParseError(
                f"{self.sso_code} prints section {printed_number} twice"
            )
        self.printed_numbers.add(printed_number)
        first_line_index = (
            self.held_headings[0].line_index if self.held_headings else line_index
        )
        if self.body_first_line_index is None:
            self.body_first_line_index = min(
                index
                for index in (
                    first_line_index,
                    self.part_first_line_index,
                    self.division_line_index,
                )
                if index is not None
            )
        self.sections.append(
            _OpenSection(
                printed_number=printed_number,
                heading=" ".join(
                    held_heading.text for held_heading in self.held_headings
                )
                if self.held_headings
                else None,
                part_heading=self.part_heading,
                division_heading=self.division_heading,
                text_lines=[line.text],
                first_page_number=(
                    self.held_headings[0].page_number
                    if self.held_headings
                    else page_number
                ),
                last_page_number=page_number,
            )
        )
        self.kept_line_indices.update(
            held_heading.line_index for held_heading in self.held_headings
        )
        self.kept_line_indices.add(line_index)
        self.held_headings = []

    def read_line(self, line: PdfLine, page_number: int) -> None:
        if self.is_body_over:
            return
        if self.quote_depth == 0 and line.text in _BODY_END_LINES:
            self.is_body_over = True
            return
        line_index = len(self.line_lengths)
        self.line_lengths.append(len(line.text))
        quote_depth_before = self.quote_depth
        self.quote_depth = max(
            0,
            self.quote_depth
            + line.text.count(_OPENING_QUOTE)
            - line.text.count(_CLOSING_QUOTE),
        )
        if quote_depth_before > 0:
            self._add_to_section_text(line.text, page_number, line_index)
            return

        if line.text.endswith(_CONTINUED_SUFFIX):
            return
        if _PART_PATTERN.match(line.text):
            self._flush_held_headings()
            self.part_heading = line.text
            self.part_first_line_index = line_index
            self.is_reading_part_title = True
            self.division_heading = None
            self.division_line_index = None
            self.kept_line_indices.add(line_index)
            return
        if (
            self.is_reading_part_title
            and self.part_heading is not None
            and not line.is_bold
            and line.text.isupper()
        ):
            self.part_heading = f"{self.part_heading}\n{line.text}"
            self.kept_line_indices.add(line_index)
            return
        self.is_reading_part_title = False
        if _DIVISION_PATTERN.match(line.text):
            self._flush_held_headings()
            self.division_heading = line.text
            self.division_line_index = line_index
            self.kept_line_indices.add(line_index)
            return

        section_number_match = _SECTION_NUMBER_PATTERN.match(line.bold_prefix)
        if section_number_match is not None:
            self._start_section(
                section_number_match.group(1), line, page_number, line_index
            )
            return
        if line.is_bold:
            self.held_headings.append(_HeldLine(line.text, page_number, line_index))
            return
        self._flush_held_headings()
        if not self.sections:
            self._clear_part_and_division()
        self._add_to_section_text(line.text, page_number, line_index)

    def get_parsed_legislation(self) -> ParsedLegislation:
        if self.quote_depth > 0:
            raise OpenSgLawSectionParseError(f"{self.sso_code} leaves a quotation open")
        self._flush_held_headings()
        if not self.sections or self.body_first_line_index is None:
            raise OpenSgLawSectionParseError(f"{self.sso_code} prints no section")
        body_first_line_index = self.body_first_line_index
        return ParsedLegislation(
            sections=[
                ParsedSection(
                    ordinal=ordinal,
                    printed_number=open_section.printed_number,
                    heading=open_section.heading,
                    part_heading=open_section.part_heading,
                    division_heading=open_section.division_heading,
                    text="\n".join(open_section.text_lines),
                    first_page_number=open_section.first_page_number,
                    last_page_number=open_section.last_page_number,
                    kind=LegislationSectionKind.SECTION,
                )
                for ordinal, open_section in enumerate(self.sections, 1)
            ],
            body_character_count=sum(self.line_lengths[body_first_line_index:]),
            section_character_count=sum(
                self.line_lengths[line_index]
                for line_index in self.kept_line_indices
                if line_index >= body_first_line_index
            ),
        )


def get_parsed_legislation(
    sso_code: str, pdf_pages: list[PdfPage]
) -> ParsedLegislation:
    section_walk = _SectionWalk(sso_code)
    for pdf_page in pdf_pages:
        for line in pdf_page.lines:
            if line.is_margin:
                continue
            section_walk.read_line(line, pdf_page.page_number)
    return section_walk.get_parsed_legislation()
