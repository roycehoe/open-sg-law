import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Union

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from enums import JudgmentBlockKind
from exceptions import OpenSgLawJudgmentParseError
from utils.elitigation_judgment import get_neutral_citation_of_tree

_JUDGMENT_SELECTOR = "#divJudgement"
_INFO_TABLE_ID = "info-table"
_FOOTNOTE_POPUP_CLASS = "modal"
_FOOTNOTE_POPUP_HEADER_CLASS = "modal-header"
_LINE_BREAK = "\n"
_CELL_SEPARATOR = "\t"
_LINE_BREAK_TAG = "br"
_TABLE_TAG = "table"
_TABLE_ROW_TAG = "tr"
_TABLE_CELL_TAGS = frozenset({"td", "th"})
_RULE_TAG = "hr"
_BLOCK_TAGS = frozenset(
    {
        "article",
        "blockquote",
        "center",
        "content",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "li",
        "ol",
        "p",
        "section",
        "table",
        "ul",
    }
)
_FRONT_MATTER_STYLES = frozenset(
    {"CaseNumber", "Citation", "NCitation", "Notice", "caseTitle", "catchwords", "title"}
)
_FRONT_MATTER_STYLE_PREFIX = "HN-"
_EDITORIAL_NOTICE_OPENING = "This judgment is subject to final editorial corrections"
_SOURCE_STYLE_PATTERN = re.compile(
    r"^(?:Judg-.+|Table-.+|Footnote|FootnoteRef|HN-.+|CaseNumber|Citation|NCitation|Notice|caseTitle|catchwords|title|txt-body)$"
)
_QUOTE_STYLE_PREFIX = "judg-quote"
_LIST_STYLE_PREFIX = "judg-list"
_FOOTNOTE_STYLE_PREFIX = "footnote"
_SIGN_OFF_STYLE = "judg-sign"
_COUNSEL_STYLE = "judg-lawyers"
_HEADING_STYLE_PATTERN = re.compile(r"^judg-.*(?:head|hdg)")
_NUMBERED_PARAGRAPH_STYLE_PATTERN = re.compile(r"^judg-\d")
_WHITESPACE_RUN_PATTERN = re.compile(r"\s+")
_SPACE_RUN_PATTERN = re.compile(r" {2,}")
_NAMED_PARAGRAPH_NUMBER_PATTERN = re.compile(r"^\[?(\d{1,4})\]?[.\s]")
_PLAIN_PARAGRAPH_NUMBER_PATTERN = re.compile(r"^(\d{1,4})\.\s")
_PRINTED_NOTE_NUMBER_PATTERN = re.compile(r"\[note: (\d+)\]")
_POPUP_TITLE_NUMBER_PATTERN = re.compile(r"(\d+)")
_FULL_DATE_PATTERN = re.compile(r"\d{1,2} [A-Z][a-z]+ \d{4}")
_FULL_DATE_FORMAT = "%d %B %Y"
_INFO_LABEL_COURT = "Tribunal/Court"
_INFO_LABEL_CASE_NUMBER = "Case Number"
_INFO_LABEL_CORAM = "Coram"
_INFO_LABEL_COUNSEL = "Counsel Name(s)"
_INFO_LABEL_CATCHWORDS = "Catchwords"
_INFO_LABEL_DECISION_DATE = "Decision Date"
_CASE_NAME_SELECTOR = ".HN-CaseName, .caseTitle"
_COURT_SELECTOR = ".title"
_CASE_NUMBER_SELECTOR = ".CaseNumber"
_CORAM_SELECTOR = ".HN-Coram"
_COUNSEL_SELECTOR = ".Judg-Lawyers"
_CATCHWORDS_SELECTOR = ".catchwords"
_DATE_RESERVED_SELECTOR = ".Judg-Date-Reserved"
_SIGN_OFF_SELECTOR = ".Judg-Sign"
_FOOTNOTE_POPUP_TITLE_SELECTOR = ".modal-title"
_INFO_ROW_SELECTOR = "tr.info-row"
_INFO_LABEL_SELECTOR = "td.txt-label"
_INFO_VALUE_SELECTOR = "td.txt-body"
_FOOTNOTE_POPUP_STYLE = "FootnoteRef"


@dataclass(frozen=True)
class ParsedJudgmentBlock:
    ordinal: int
    printed_number: Optional[str]
    text: str
    source_style: Optional[str]
    kind: JudgmentBlockKind


@dataclass(frozen=True)
class JudgmentDetails:
    case_name: Optional[str]
    printed_court: Optional[str]
    printed_case_number: Optional[str]
    printed_coram: Optional[str]
    printed_counsel: Optional[str]
    printed_catchwords: Optional[str]
    printed_decision_date: Optional[str]


@dataclass(frozen=True)
class ParsedJudgment:
    neutral_citation: str
    details: JudgmentDetails
    decision_date: Optional[date]
    blocks: list[ParsedJudgmentBlock]
    body_character_count: int
    block_character_count: int


@dataclass(frozen=True)
class _DraftBlock:
    printed_number: Optional[str]
    text: str
    source_style: Optional[str]
    kind: JudgmentBlockKind


def _has_class(element: Tag, class_name: str) -> bool:
    return class_name in (element.get("class") or [])


def _get_element_strings(element: Tag, skipped_class: str) -> Iterator[str]:
    for child in element.children:
        if isinstance(child, Tag):
            if child.name == _LINE_BREAK_TAG:
                yield _LINE_BREAK
                continue
            if not _has_class(child, skipped_class):
                yield from _get_element_strings(child, skipped_class)
        elif type(child) is NavigableString:
            yield _WHITESPACE_RUN_PATTERN.sub(" ", child)


def _get_lines_text(raw_text: str) -> str:
    stripped_lines = [
        _SPACE_RUN_PATTERN.sub(" ", line).strip() for line in raw_text.split(_LINE_BREAK)
    ]
    return _LINE_BREAK.join(line for line in stripped_lines if line)


def _get_element_text(element: Tag) -> str:
    return _get_lines_text(
        "".join(_get_element_strings(element, _FOOTNOTE_POPUP_CLASS))
    )


def _get_table_text(table: Tag) -> str:
    row_texts = []
    for table_row in table.find_all(_TABLE_ROW_TAG):
        if table_row.find_parent(_TABLE_TAG) is not table:
            continue
        cell_texts = [
            _get_element_text(table_cell).replace(_LINE_BREAK, " ")
            for table_cell in table_row.find_all(_TABLE_CELL_TAGS, recursive=False)
        ]
        row_text = _CELL_SEPARATOR.join(
            cell_text for cell_text in cell_texts if cell_text
        )
        if row_text:
            row_texts.append(row_text)
    return _LINE_BREAK.join(row_texts)


def _get_character_count(text: str) -> int:
    return len(_WHITESPACE_RUN_PATTERN.sub("", text))


def _get_source_style(element: Tag) -> Optional[str]:
    for class_name in element.get("class") or []:
        if _SOURCE_STYLE_PATTERN.match(class_name) is not None:
            return class_name
    return None


def _has_block_descendant(element: Tag) -> bool:
    return any(
        descendant.find_parent(class_=_FOOTNOTE_POPUP_CLASS) is None
        for descendant in element.find_all(_BLOCK_TAGS)
        if not _has_class(descendant, _FOOTNOTE_POPUP_CLASS)
    )


def _is_block_element(element: Tag) -> bool:
    if element.name == _TABLE_TAG:
        return True
    if _has_class(element, _FOOTNOTE_POPUP_CLASS):
        return True
    if _get_source_style(element) is not None:
        return True
    return not _has_block_descendant(element)


def _get_block_nodes(parent: Tag) -> Iterator[Union[Tag, NavigableString]]:
    for child in parent.children:
        if isinstance(child, Tag):
            if _is_block_element(child):
                yield child
            else:
                yield from _get_block_nodes(child)
        elif type(child) is NavigableString:
            yield child


def _get_style_kind(source_style: Optional[str]) -> JudgmentBlockKind:
    if source_style is None:
        return JudgmentBlockKind.PLAIN
    lower_style = source_style.lower()
    if lower_style.startswith(_QUOTE_STYLE_PREFIX):
        return JudgmentBlockKind.QUOTE
    if lower_style.startswith(_LIST_STYLE_PREFIX):
        return JudgmentBlockKind.LIST
    if _HEADING_STYLE_PATTERN.match(lower_style) is not None:
        return JudgmentBlockKind.HEADING
    if lower_style.startswith(_FOOTNOTE_STYLE_PREFIX):
        return JudgmentBlockKind.FOOTNOTE
    if lower_style == _SIGN_OFF_STYLE:
        return JudgmentBlockKind.SIGN_OFF
    if lower_style == _COUNSEL_STYLE:
        return JudgmentBlockKind.COUNSEL
    if _NUMBERED_PARAGRAPH_STYLE_PATTERN.match(lower_style) is not None:
        return JudgmentBlockKind.PARAGRAPH
    if (
        source_style in _FRONT_MATTER_STYLES
        or source_style.startswith(_FRONT_MATTER_STYLE_PREFIX)
    ):
        return JudgmentBlockKind.FRONT_MATTER
    return JudgmentBlockKind.PLAIN


def _get_element_kind(element: Tag, text: str) -> JudgmentBlockKind:
    if element.name != _TABLE_TAG:
        return _get_style_kind(_get_source_style(element))
    if text.startswith(_EDITORIAL_NOTICE_OPENING):
        return JudgmentBlockKind.FRONT_MATTER
    if element.select_one(_SIGN_OFF_SELECTOR) is not None:
        return JudgmentBlockKind.SIGN_OFF
    return JudgmentBlockKind.TABLE


def _get_match_number(pattern: re.Pattern[str], text: str) -> Optional[str]:
    match = pattern.search(text)
    if match is None:
        return None
    return match.group(1)


def _get_printed_number(kind: JudgmentBlockKind, text: str) -> Optional[str]:
    if kind == JudgmentBlockKind.PARAGRAPH:
        return _get_match_number(_NAMED_PARAGRAPH_NUMBER_PATTERN, text)
    if kind == JudgmentBlockKind.PLAIN:
        return _get_match_number(_PLAIN_PARAGRAPH_NUMBER_PATTERN, text)
    if kind == JudgmentBlockKind.FOOTNOTE:
        return _get_match_number(_PRINTED_NOTE_NUMBER_PATTERN, text)
    return None


def _build_footnote_popup_block(footnote_popup: Tag) -> _DraftBlock:
    popup_title = footnote_popup.select_one(_FOOTNOTE_POPUP_TITLE_SELECTOR)
    return _DraftBlock(
        printed_number=(
            None
            if popup_title is None
            else _get_match_number(
                _POPUP_TITLE_NUMBER_PATTERN, popup_title.get_text()
            )
        ),
        text=_get_lines_text(
            "".join(_get_element_strings(footnote_popup, _FOOTNOTE_POPUP_HEADER_CLASS))
        ),
        source_style=_FOOTNOTE_POPUP_STYLE,
        kind=JudgmentBlockKind.FOOTNOTE,
    )


def _build_element_block(element: Tag, is_front_matter: bool) -> _DraftBlock:
    text = (
        _get_table_text(element)
        if element.name == _TABLE_TAG
        else _get_element_text(element)
    )
    element_kind = _get_element_kind(element, text)
    kind = (
        JudgmentBlockKind.FRONT_MATTER
        if is_front_matter and element_kind != JudgmentBlockKind.COUNSEL
        else element_kind
    )
    return _DraftBlock(
        printed_number=_get_printed_number(kind, text),
        text=text,
        source_style=_get_source_style(element),
        kind=kind,
    )


def _get_draft_blocks(judgment_root: Tag) -> Iterator[_DraftBlock]:
    is_front_matter = (
        judgment_root.find(_RULE_TAG) is not None
        or judgment_root.find(id=_INFO_TABLE_ID) is not None
    )
    for block_node in _get_block_nodes(judgment_root):
        if not isinstance(block_node, Tag):
            text = _get_lines_text(_WHITESPACE_RUN_PATTERN.sub(" ", block_node))
            kind = (
                JudgmentBlockKind.FRONT_MATTER
                if is_front_matter
                else JudgmentBlockKind.PLAIN
            )
            yield _DraftBlock(_get_printed_number(kind, text), text, None, kind)
            continue
        if _has_class(block_node, _FOOTNOTE_POPUP_CLASS):
            yield _build_footnote_popup_block(block_node)
            continue
        yield _build_element_block(block_node, is_front_matter)
        for footnote_popup in block_node.find_all(class_=_FOOTNOTE_POPUP_CLASS):
            yield _build_footnote_popup_block(footnote_popup)
        if block_node.name == _RULE_TAG or block_node.get("id") == _INFO_TABLE_ID:
            is_front_matter = False


def _get_first_text(judgment_root: Tag, selector: str) -> Optional[str]:
    element = judgment_root.select_one(selector)
    if element is None:
        return None
    return _get_element_text(element) or None


def _get_case_name(judgment_root: Tag) -> Optional[str]:
    case_name = _get_first_text(judgment_root, _CASE_NAME_SELECTOR)
    if case_name is None:
        return None
    return case_name.replace(_LINE_BREAK, " ")


def _get_joined_text(judgment_root: Tag, selector: str) -> Optional[str]:
    texts = [_get_element_text(element) for element in judgment_root.select(selector)]
    return _LINE_BREAK.join(text for text in texts if text) or None


def _get_info_label_to_value(judgment_root: Tag) -> dict[str, str]:
    info_label_to_value = {}
    for info_row in judgment_root.select(_INFO_ROW_SELECTOR):
        label_cell = info_row.select_one(_INFO_LABEL_SELECTOR)
        value_cell = info_row.select_one(_INFO_VALUE_SELECTOR)
        if label_cell is None or value_cell is None:
            continue
        info_label_to_value[_get_element_text(label_cell)] = _get_element_text(
            value_cell
        )
    return info_label_to_value


def _build_info_table_details(
    judgment_root: Tag, info_label_to_value: dict[str, str]
) -> JudgmentDetails:
    return JudgmentDetails(
        case_name=_get_case_name(judgment_root),
        printed_court=info_label_to_value.get(_INFO_LABEL_COURT) or None,
        printed_case_number=info_label_to_value.get(_INFO_LABEL_CASE_NUMBER) or None,
        printed_coram=info_label_to_value.get(_INFO_LABEL_CORAM) or None,
        printed_counsel=info_label_to_value.get(_INFO_LABEL_COUNSEL) or None,
        printed_catchwords=info_label_to_value.get(_INFO_LABEL_CATCHWORDS) or None,
        printed_decision_date=info_label_to_value.get(_INFO_LABEL_DECISION_DATE)
        or None,
    )


def _get_header_decision_date(judgment_root: Tag) -> Optional[str]:
    for date_reserved_element in judgment_root.select(_DATE_RESERVED_SELECTOR):
        date_reserved_text = _get_element_text(date_reserved_element)
        if _FULL_DATE_PATTERN.match(date_reserved_text) is not None:
            return date_reserved_text
    coram_text = _get_first_text(judgment_root, _CORAM_SELECTOR)
    if coram_text is None:
        return None
    last_coram_line = coram_text.split(_LINE_BREAK)[-1]
    if _FULL_DATE_PATTERN.fullmatch(last_coram_line) is None:
        return None
    return last_coram_line


def _build_header_details(judgment_root: Tag) -> JudgmentDetails:
    return JudgmentDetails(
        case_name=_get_case_name(judgment_root),
        printed_court=_get_first_text(judgment_root, _COURT_SELECTOR),
        printed_case_number=_get_first_text(judgment_root, _CASE_NUMBER_SELECTOR),
        printed_coram=_get_first_text(judgment_root, _CORAM_SELECTOR),
        printed_counsel=_get_joined_text(judgment_root, _COUNSEL_SELECTOR),
        printed_catchwords=_get_joined_text(judgment_root, _CATCHWORDS_SELECTOR),
        printed_decision_date=_get_header_decision_date(judgment_root),
    )


def _get_details(judgment_root: Tag) -> JudgmentDetails:
    info_label_to_value = _get_info_label_to_value(judgment_root)
    if not info_label_to_value:
        return _build_header_details(judgment_root)
    return _build_info_table_details(judgment_root, info_label_to_value)


def _get_decision_date(printed_decision_date: Optional[str]) -> Optional[date]:
    if printed_decision_date is None:
        return None
    match = _FULL_DATE_PATTERN.search(printed_decision_date)
    if match is None:
        return None
    try:
        return datetime.strptime(match.group(0), _FULL_DATE_FORMAT).date()
    except ValueError:
        return None


def get_parsed_judgment(judgment_html: str) -> ParsedJudgment:
    judgment_tree = BeautifulSoup(judgment_html, "html.parser")
    neutral_citation = get_neutral_citation_of_tree(judgment_tree)
    if neutral_citation is None:
        raise OpenSgLawJudgmentParseError("The page title is not a neutral citation")
    judgment_root = judgment_tree.select_one(_JUDGMENT_SELECTOR)
    if judgment_root is None:
        raise OpenSgLawJudgmentParseError(f"{neutral_citation} holds no judgment body")
    draft_blocks = [
        draft_block
        for draft_block in _get_draft_blocks(judgment_root)
        if draft_block.text
    ]
    if not draft_blocks:
        raise OpenSgLawJudgmentParseError(f"{neutral_citation} holds no text")
    details = _get_details(judgment_root)
    return ParsedJudgment(
        neutral_citation=neutral_citation,
        details=details,
        decision_date=_get_decision_date(details.printed_decision_date),
        blocks=[
            ParsedJudgmentBlock(
                ordinal=ordinal,
                printed_number=draft_block.printed_number,
                text=draft_block.text,
                source_style=draft_block.source_style,
                kind=draft_block.kind,
            )
            for ordinal, draft_block in enumerate(draft_blocks)
        ],
        body_character_count=_get_character_count(
            "".join(_get_element_strings(judgment_root, _FOOTNOTE_POPUP_HEADER_CLASS))
        ),
        block_character_count=sum(
            _get_character_count(draft_block.text) for draft_block in draft_blocks
        ),
    )
