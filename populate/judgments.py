from dataclasses import dataclass

from sqlmodel import Session

from crud.judgment import CRUDJudgment, JudgmentRow
from crud.judgment_block import CRUDJudgmentBlock, JudgmentBlockRow
from crud.source_response import CRUDSourceResponse, DocumentRow
from database.judgment import Judgment, JudgmentBlock
from exceptions import OpenSgLawWriteCheckError
from services.judgment import ParsedJudgment, get_parsed_judgment


@dataclass(frozen=True)
class JudgmentParse:
    elitigation_url: str
    source_response_id: int
    parsed_judgment: ParsedJudgment
    is_changed: bool


def _build_judgment_row(
    source_response_id: int, parsed_judgment: ParsedJudgment
) -> JudgmentRow:
    return JudgmentRow(
        neutral_citation=parsed_judgment.neutral_citation,
        case_name=parsed_judgment.details.case_name,
        printed_court=parsed_judgment.details.printed_court,
        printed_case_number=parsed_judgment.details.printed_case_number,
        printed_coram=parsed_judgment.details.printed_coram,
        printed_counsel=parsed_judgment.details.printed_counsel,
        printed_catchwords=parsed_judgment.details.printed_catchwords,
        printed_decision_date=parsed_judgment.details.printed_decision_date,
        decision_date=parsed_judgment.decision_date,
        body_character_count=parsed_judgment.body_character_count,
        block_character_count=parsed_judgment.block_character_count,
        source_response_id=source_response_id,
    )


def _build_judgment_block_rows(
    parsed_judgment: ParsedJudgment,
) -> list[JudgmentBlockRow]:
    return [
        JudgmentBlockRow(
            ordinal=parsed_block.ordinal,
            printed_number=parsed_block.printed_number,
            text=parsed_block.text,
            source_style=parsed_block.source_style,
            kind=parsed_block.kind,
        )
        for parsed_block in parsed_judgment.blocks
    ]


def _is_judgment_changed(
    session: Session,
    elitigation_url: str,
    source_response_id: int,
    parsed_judgment: ParsedJudgment,
) -> bool:
    judgment_id = CRUDJudgment(session).get_id_by_elitigation_url(elitigation_url)
    if judgment_id is None:
        return True
    if CRUDJudgment(session).get_row_by_id(judgment_id) != _build_judgment_row(
        source_response_id, parsed_judgment
    ):
        return True
    return CRUDJudgmentBlock(session).get_rows_by_judgment_id(
        judgment_id
    ) != _build_judgment_block_rows(parsed_judgment)


def get_judgment_parse(session: Session, document_row: DocumentRow) -> JudgmentParse:
    parsed_judgment = get_parsed_judgment(
        CRUDSourceResponse(session).get_body_text_by_id_and_body_text_not_null(
            document_row.id
        )
    )
    return JudgmentParse(
        elitigation_url=document_row.requested_url,
        source_response_id=document_row.id,
        parsed_judgment=parsed_judgment,
        is_changed=_is_judgment_changed(
            session, document_row.requested_url, document_row.id, parsed_judgment
        ),
    )


def _delete_stored_judgment(session: Session, elitigation_url: str) -> None:
    judgment_id = CRUDJudgment(session).get_id_by_elitigation_url(elitigation_url)
    if judgment_id is None:
        return
    CRUDJudgmentBlock(session).delete_by_judgment_id(judgment_id)
    CRUDJudgment(session).delete_by_id(judgment_id)


def write_judgment(session: Session, judgment_parse: JudgmentParse) -> int:
    _delete_stored_judgment(session, judgment_parse.elitigation_url)
    parsed_judgment = judgment_parse.parsed_judgment
    judgment = Judgment(
        elitigation_url=judgment_parse.elitigation_url,
        neutral_citation=parsed_judgment.neutral_citation,
        case_name=parsed_judgment.details.case_name,
        printed_court=parsed_judgment.details.printed_court,
        printed_case_number=parsed_judgment.details.printed_case_number,
        printed_coram=parsed_judgment.details.printed_coram,
        printed_counsel=parsed_judgment.details.printed_counsel,
        printed_catchwords=parsed_judgment.details.printed_catchwords,
        printed_decision_date=parsed_judgment.details.printed_decision_date,
        decision_date=parsed_judgment.decision_date,
        body_character_count=parsed_judgment.body_character_count,
        block_character_count=parsed_judgment.block_character_count,
        source_response_id=judgment_parse.source_response_id,
    )
    CRUDJudgment(session).add(judgment)
    judgment_id = judgment.id
    if judgment_id is None:
        raise OpenSgLawWriteCheckError(
            f"The judgment row of {judgment_parse.elitigation_url} has no id after the flush"
        )
    CRUDJudgmentBlock(session).add_many(
        [
            JudgmentBlock(
                ordinal=parsed_block.ordinal,
                printed_number=parsed_block.printed_number,
                text=parsed_block.text,
                source_style=parsed_block.source_style,
                kind=parsed_block.kind,
                judgment_id=judgment_id,
            )
            for parsed_block in parsed_judgment.blocks
        ]
    )
    return judgment_id
