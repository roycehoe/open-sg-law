from dataclasses import dataclass
from typing import Optional

from sqlmodel import Session, col, delete, func, select

from database.judgment import JudgmentBlock
from enums import JudgmentBlockKind


@dataclass(frozen=True)
class JudgmentBlockRow:
    ordinal: int
    printed_number: Optional[str]
    text: str
    source_style: Optional[str]
    kind: JudgmentBlockKind


class CRUDJudgmentBlock:
    def __init__(self, session: Session):
        self.session = session

    def add_many(self, judgment_blocks: list[JudgmentBlock]) -> None:
        self.session.add_all(judgment_blocks)
        self.session.flush()

    def get_count_by_judgment_id(self, judgment_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(JudgmentBlock)
            .where(col(JudgmentBlock.judgment_id) == judgment_id)
        )
        return self.session.exec(statement).one()

    def get_rows_by_judgment_id(self, judgment_id: int) -> list[JudgmentBlockRow]:
        statement = (
            select(  # pyright: ignore[reportCallIssue] sqlmodel types select for at most four columns
                JudgmentBlock.ordinal,
                JudgmentBlock.printed_number,
                JudgmentBlock.text,
                JudgmentBlock.source_style,
                JudgmentBlock.kind,
            )
            .where(col(JudgmentBlock.judgment_id) == judgment_id)
            .order_by(JudgmentBlock.ordinal)
        )
        return [JudgmentBlockRow(*row) for row in self.session.exec(statement).all()]

    def delete_by_judgment_id(self, judgment_id: int) -> None:
        statement = delete(JudgmentBlock).where(
            col(JudgmentBlock.judgment_id) == judgment_id
        )
        self.session.execute(statement)
        self.session.flush()
