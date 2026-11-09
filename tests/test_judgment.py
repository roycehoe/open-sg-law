from datetime import date
from pathlib import Path

import pytest

from enums import JudgmentBlockKind
from exceptions import OpenSgLawJudgmentParseError
from services.judgment import ParsedJudgment, get_parsed_judgment
from utils.elitigation_judgment import get_elitigation_neutral_citation

_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures" / "elitigation"
_HEADER_LAYOUT_HTML = """<html><head><title>[2099] SGHC 1</title></head><body>
<div id="divCaseSummary"></div><div id="divJudgement"><content>
<div class="row"><div class="col"><div class="title"><span>In the High Court</span></div>
<div class="HN-NeutralCit">[2099] SGHC 1</div><div class="CaseNumber">Suit 1 of 2099</div>
<div class="txt-body">Between</div><table><tbody><tr><td></td><td>Alpha</td></tr></tbody></table>
<div class="catchwords">Tort  —
 Negligence</div></div></div><hr>
<div class="row"><div class="col"><table><tbody><tr><td>This judgment is subject to final editorial corrections approved by the court.</td></tr></tbody></table>
<div class="HN-CaseName">Alpha v Beta</div><div class="HN-CaseName">[2099] SGHC 1</div>
<div class="HN-Coram">Suit 1 of 2099<br>Gamma J<br>1, 2 March 2099</div>
<div class="Judg-Date-Reserved">4 April 2099<br>Judgment reserved.</div>
<div class="Judg-Author">Gamma J:</div>
<div class="Judg-Heading-1">Facts</div>
<div class="Judg-1">1 Alpha sued.<sup><button>1</button></sup><div class="modal fade" id="fn-1"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Foot Note 1</h5><button><span>x</span></button></div><div class="modal-body"><div class="FootnoteRef">Affidavit at p 1.</div></div></div></div></div></div>
<div class="Judg-1">Alpha then lost.</div>
<div class="Judg-Quote-0">A quoted line.</div>
<div class="Judg-List-1">(a) a point</div>
<table><tbody><tr><td>Band</td><td>$1</td></tr><tr><td>Other</td><td>$2</td></tr></tbody></table>
<table class="table-borderless"><tbody><tr><td><div class="Judg-Sign">Gamma J</div></td></tr></tbody></table>
<div class="Judg-Lawyers">A for the plaintiff;<br>B for the defendant.</div><div class="Judg-EOF"></div>
</div></div></content></div></body></html>"""
_PLAIN_LAYOUT_HTML = """<html><head><title>[2001] SGHC 2</title></head><body><div id="divJudgement">
<div class="contentsOfFile"><h2 class="title"><span class="caseTitle">Alpha <em>v</em> Beta</span><br><span class="NCitation">[2001] SGHC 2</span></h2>
<table id="info-table"><tbody>
<tr class="info-row"><td class="txt-label">Case Number</td><td class="info-delim1">:</td><td class="txt-body"><casenumber>Suit 2/2001</casenumber></td></tr>
<tr class="info-row"><td class="txt-label">Decision Date</td><td class="info-delim1">:</td><td class="txt-body">23 October 2001</td></tr>
<tr class="info-row"><td class="txt-label">Tribunal/Court</td><td class="info-delim1">:</td><td class="txt-body">High Court</td></tr>
<tr class="info-row"><td class="txt-label">Coram</td><td class="info-delim1">:</td><td class="txt-body">Gamma JC</td></tr>
<tr class="info-row"><td class="txt-label">Counsel Name(s)</td><td class="info-delim1">:</td><td class="txt-body">A for the plaintiff</td></tr>
</tbody></table>
<p>1. Alpha sued Beta.</p><p>Some loose words.</p><p>2. Beta won.</p>
<p>Sgd:</p><p>GAMMA<br>JUDICIAL COMMISSIONER</p>
<p class="Footnote"><sup><a id="Ftn_1">[note: 1]</a></sup>Affidavit at p 1.</p>
</div><div></div><p>Copyright © Government of Singapore.</p></div></body></html>"""
_MAINTENANCE_NOTICE_HTML = (
    "<html><head><title>:: eLitigation - Maintenance Notice ::</title></head></html>"
)
_NO_BODY_HTML = "<html><head><title>[2099] SGHC 1</title></head><body></body></html>"
_EMPTY_BODY_HTML = '<html><head><title>[2099] SGHC 1</title></head><body><div id="divJudgement"><p></p></div></body></html>'


def _get_kinds_and_texts(
    parsed_judgment: ParsedJudgment,
) -> list[tuple[JudgmentBlockKind, str]]:
    return [(block.kind, block.text) for block in parsed_judgment.blocks]


def test_a_header_page_reads_what_it_prints() -> None:
    parsed_judgment = get_parsed_judgment(_HEADER_LAYOUT_HTML)

    assert parsed_judgment.neutral_citation == "[2099] SGHC 1"
    assert parsed_judgment.details.case_name == "Alpha v Beta"
    assert parsed_judgment.details.printed_court == "In the High Court"
    assert parsed_judgment.details.printed_case_number == "Suit 1 of 2099"
    assert parsed_judgment.details.printed_catchwords == "Tort — Negligence"
    assert (
        parsed_judgment.details.printed_counsel
        == "A for the plaintiff;\nB for the defendant."
    )
    assert parsed_judgment.details.printed_decision_date == "4 April 2099\nJudgment reserved."
    assert parsed_judgment.decision_date == date(2099, 4, 4)


def test_a_header_page_keeps_every_block_in_order_and_every_character() -> None:
    parsed_judgment = get_parsed_judgment(_HEADER_LAYOUT_HTML)

    assert _get_kinds_and_texts(parsed_judgment)[-9:] == [
        (JudgmentBlockKind.HEADING, "Facts"),
        (JudgmentBlockKind.PARAGRAPH, "1 Alpha sued.1"),
        (JudgmentBlockKind.FOOTNOTE, "Affidavit at p 1."),
        (JudgmentBlockKind.PARAGRAPH, "Alpha then lost."),
        (JudgmentBlockKind.QUOTE, "A quoted line."),
        (JudgmentBlockKind.LIST, "(a) a point"),
        (JudgmentBlockKind.TABLE, "Band\t$1\nOther\t$2"),
        (JudgmentBlockKind.SIGN_OFF, "Gamma J"),
        (JudgmentBlockKind.COUNSEL, "A for the plaintiff;\nB for the defendant."),
    ]
    assert [block.ordinal for block in parsed_judgment.blocks] == list(
        range(len(parsed_judgment.blocks))
    )
    assert (
        parsed_judgment.block_character_count == parsed_judgment.body_character_count
    )


def test_blocks_before_the_rule_and_the_editorial_notice_are_front_matter() -> None:
    parsed_judgment = get_parsed_judgment(_HEADER_LAYOUT_HTML)

    front_matter_texts = [
        block.text
        for block in parsed_judgment.blocks
        if block.kind == JudgmentBlockKind.FRONT_MATTER
    ]

    assert "Between" in front_matter_texts
    assert "Alpha" in front_matter_texts
    assert (
        "This judgment is subject to final editorial corrections approved by the court."
        in front_matter_texts
    )
    assert "Alpha v Beta" in front_matter_texts


def test_a_paragraph_number_is_read_only_where_one_is_printed() -> None:
    parsed_judgment = get_parsed_judgment(_HEADER_LAYOUT_HTML)

    numbered_paragraphs = {
        block.text: block.printed_number
        for block in parsed_judgment.blocks
        if block.kind == JudgmentBlockKind.PARAGRAPH
    }

    assert numbered_paragraphs == {"1 Alpha sued.1": "1", "Alpha then lost.": None}


def test_a_footnote_popup_follows_its_paragraph_with_its_number() -> None:
    parsed_judgment = get_parsed_judgment(_HEADER_LAYOUT_HTML)

    footnote = next(
        block
        for block in parsed_judgment.blocks
        if block.kind == JudgmentBlockKind.FOOTNOTE
    )
    paragraph_before = parsed_judgment.blocks[footnote.ordinal - 1]

    assert footnote.text == "Affidavit at p 1."
    assert footnote.printed_number == "1"
    assert paragraph_before.text == "1 Alpha sued.1"


def test_a_plain_page_reads_the_info_table_and_keeps_its_paragraphs() -> None:
    parsed_judgment = get_parsed_judgment(_PLAIN_LAYOUT_HTML)

    assert parsed_judgment.details.case_name == "Alpha v Beta"
    assert parsed_judgment.details.printed_court == "High Court"
    assert parsed_judgment.details.printed_case_number == "Suit 2/2001"
    assert parsed_judgment.details.printed_coram == "Gamma JC"
    assert parsed_judgment.details.printed_counsel == "A for the plaintiff"
    assert parsed_judgment.details.printed_catchwords is None
    assert parsed_judgment.decision_date == date(2001, 10, 23)
    body_blocks = [
        (block.printed_number, block.text, block.kind)
        for block in parsed_judgment.blocks
        if block.kind != JudgmentBlockKind.FRONT_MATTER
    ]
    assert body_blocks == [
        ("1", "1. Alpha sued Beta.", JudgmentBlockKind.PLAIN),
        (None, "Some loose words.", JudgmentBlockKind.PLAIN),
        ("2", "2. Beta won.", JudgmentBlockKind.PLAIN),
        (None, "Sgd:", JudgmentBlockKind.PLAIN),
        (None, "GAMMA\nJUDICIAL COMMISSIONER", JudgmentBlockKind.PLAIN),
        ("1", "[note: 1]Affidavit at p 1.", JudgmentBlockKind.FOOTNOTE),
        (None, "Copyright © Government of Singapore.", JudgmentBlockKind.PLAIN),
    ]
    assert (
        parsed_judgment.block_character_count == parsed_judgment.body_character_count
    )


def test_a_real_page_lands_all_its_text_in_blocks() -> None:
    parsed_judgment = get_parsed_judgment(
        (_FIXTURES_DIRECTORY / "judgment-2025-sghc-267.html").read_text()
    )

    assert parsed_judgment.neutral_citation == "[2025] SGHC 267"
    assert (
        parsed_judgment.details.case_name
        == "Wish Controls Pte Ltd v Trident Water Systems Pte Ltd"
    )
    assert parsed_judgment.decision_date == date(2025, 12, 31)
    assert (
        parsed_judgment.block_character_count == parsed_judgment.body_character_count
    )
    assert JudgmentBlockKind.PARAGRAPH in {
        block.kind for block in parsed_judgment.blocks
    }


@pytest.mark.parametrize(
    ("source_style", "expected_kind"),
    [
        ("Judg-quote-1", JudgmentBlockKind.QUOTE),
        ("Judg-Quote-Heading1", JudgmentBlockKind.QUOTE),
        ("Judg-QuoteList-2", JudgmentBlockKind.QUOTE),
        ("Judg-list-1", JudgmentBlockKind.LIST),
        ("Judg-heading-1", JudgmentBlockKind.HEADING),
        ("Judg-Headg-2", JudgmentBlockKind.HEADING),
        ("Judg-2-heading", JudgmentBlockKind.HEADING),
        ("Judg-1-firstpara", JudgmentBlockKind.PARAGRAPH),
        ("Judg-2-tblr", JudgmentBlockKind.PARAGRAPH),
        ("Judg-author", JudgmentBlockKind.PLAIN),
    ],
)
def test_a_style_is_read_however_the_court_spells_it(
    source_style: str, expected_kind: JudgmentBlockKind
) -> None:
    parsed_judgment = get_parsed_judgment(
        f'<title>[2099] SGHC 1</title><div id="divJudgement"><div class="{source_style}">Words.</div></div>'
    )

    assert parsed_judgment.blocks[0].kind == expected_kind
    assert parsed_judgment.blocks[0].source_style == source_style


def test_text_no_block_holds_lowers_the_block_count_below_the_body_count() -> None:
    parsed_judgment = get_parsed_judgment(
        '<title>[2099] SGHC 1</title><div id="divJudgement"><table>stray words<tr><td>Cell</td></tr></table></div>'
    )

    assert parsed_judgment.body_character_count > parsed_judgment.block_character_count


def test_a_date_that_cannot_be_read_is_left_empty_and_the_print_is_kept() -> None:
    parsed_judgment = get_parsed_judgment(
        _PLAIN_LAYOUT_HTML.replace("23 October 2001", "31 Octember 2001")
    )

    assert parsed_judgment.details.printed_decision_date == "31 Octember 2001"
    assert parsed_judgment.decision_date is None


@pytest.mark.parametrize(
    "printed_hearing_dates",
    [
        "5 &amp; 16 September 2025",
        "High Court<br>George Wei J<br>2 August 2016; 30 September 2016",
    ],
)
def test_a_list_of_hearing_dates_is_not_read_as_the_decision_date(
    printed_hearing_dates: str,
) -> None:
    parsed_judgment = get_parsed_judgment(
        _HEADER_LAYOUT_HTML.replace(
            "4 April 2099<br>Judgment reserved.", printed_hearing_dates
        )
    )

    assert parsed_judgment.details.printed_decision_date is None
    assert parsed_judgment.decision_date is None


def test_a_decision_date_printed_after_a_list_of_hearing_dates_is_read() -> None:
    parsed_judgment = get_parsed_judgment(
        _HEADER_LAYOUT_HTML.replace(
            '<div class="Judg-Date-Reserved">4 April 2099<br>Judgment reserved.</div>',
            '<div class="Judg-Date-Reserved">High Court<br>1 March; 2 April 2099</div>'
            '<div class="Judg-Date-Reserved">4 April 2099 Judgment reserved.</div>',
        )
    )

    assert parsed_judgment.decision_date == date(2099, 4, 4)


def test_text_a_stray_tag_traps_inside_a_footnote_popup_is_kept() -> None:
    parsed_judgment = get_parsed_judgment(
        '''<title>[2099] SGHC 1</title><div id="divJudgement"><div class="Judg-1">1 Words.<div class="modal fade"><div class="modal-dialog"><div class="modal-content"><div class="modal-header"><h5 class="modal-title">Foot Note 1</h5></div><div class="modal-body"><div class="FootnoteRef">Report, page 1 <Attitudes>Note</div></div></div></div>The trapped words.</div></div>'''
    )

    assert (
        parsed_judgment.block_character_count == parsed_judgment.body_character_count
    )


def test_a_citation_printed_with_no_space_is_accepted_as_printed() -> None:
    assert (
        get_elitigation_neutral_citation("<title>[2013] SGHC115</title>")
        == "[2013] SGHC115"
    )


def test_a_maintenance_notice_is_refused() -> None:
    with pytest.raises(OpenSgLawJudgmentParseError, match="not a neutral citation"):
        get_parsed_judgment(_MAINTENANCE_NOTICE_HTML)


def test_a_page_with_no_judgment_body_is_refused() -> None:
    with pytest.raises(OpenSgLawJudgmentParseError, match="no judgment body"):
        get_parsed_judgment(_NO_BODY_HTML)


def test_a_judgment_body_with_no_text_is_refused() -> None:
    with pytest.raises(OpenSgLawJudgmentParseError, match="no text"):
        get_parsed_judgment(_EMPTY_BODY_HTML)
