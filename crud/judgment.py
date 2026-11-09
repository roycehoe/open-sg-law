from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlmodel import Session, col, delete, func, select

from database.judgment import Judgment


@dataclass(frozen=True)
class JudgmentRow:
    neutral_citation: str
    case_name: Optional[str]
    printed_court: Optional[str]
    printed_case_number: Optional[str]
    printed_coram: Optional[str]
    printed_counsel: Optional[str]
    printed_catchwords: Optional[str]
    printed_decision_date: Optional[str]
    decision_date: Optional[date]
    body_character_count: int
    block_character_count: int
    source_response_id: int


class CRUDJudgment:
    def __init__(self, session: Session):
        self.session = session

    def add(self, judgment: Judgment) -> None:
        self.session.add(judgment)
        self.session.flush()

    def get_count(self) -> int:
        statement = select(func.count()).select_from(Judgment)
        return self.session.exec(statement).one()

    def get_id_by_elitigation_url(self, elitigation_url: str) -> Optional[int]:
        statement = select(Judgment.id).where(
            col(Judgment.elitigation_url) == elitigation_url
        )
        return self.session.exec(statement).one_or_none()

    def get_row_by_id(self, judgment_id: int) -> JudgmentRow:
        statement = select(  # pyright: ignore[reportCallIssue] sqlmodel types select for at most four columns
            Judgment.neutral_citation,
            Judgment.case_name,
            Judgment.printed_court,
            Judgment.printed_case_number,
            Judgment.printed_coram,
            Judgment.printed_counsel,
            Judgment.printed_catchwords,
            Judgment.printed_decision_date,
            Judgment.decision_date,
            Judgment.body_character_count,
            Judgment.block_character_count,
            Judgment.source_response_id,
        ).where(col(Judgment.id) == judgment_id)
        return JudgmentRow(*self.session.exec(statement).one())

    def delete_by_id(self, judgment_id: int) -> None:
        statement = delete(Judgment).where(col(Judgment.id) == judgment_id)
        self.session.execute(statement)
        self.session.flush()
