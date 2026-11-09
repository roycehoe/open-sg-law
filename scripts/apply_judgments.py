import argparse
from collections import Counter
from dataclasses import dataclass

from sqlmodel import Session

from crud.judgment_block import CRUDJudgmentBlock
from crud.source_response import CRUDSourceResponse
from database.init import engine
from database.judgment import Judgment, JudgmentBlock
from enums import JudgmentBlockKind, ResponseKind, SourceName
from exceptions import OpenSgLawJudgmentParseError, OpenSgLawWriteCheckError
from logs import logger
from populate.judgments import JudgmentParse, get_judgment_parse, write_judgment
from populate.written_tables import vacuum_analyze_written_tables
from services.judgment import ParsedJudgment
from settings import settings
from utils.write_target import validate_can_write

_HTTP_OK = 200
_LOW_TEXT_SHARE = 0.99
_MAX_LISTED_LOW_SHARE_JUDGMENTS = 40
_PROGRESS_EVERY_JUDGMENTS = 1_000


@dataclass(frozen=True)
class _UnparsedJudgment:
    elitigation_url: str
    reason: str


class _JudgmentFigures:
    def __init__(self):
        self.kind_to_block_count: Counter[JudgmentBlockKind] = Counter()
        self.source_style_to_block_count: Counter[str] = Counter()
        self.empty_field_to_judgment_count: Counter[str] = Counter()
        self.no_decision_date_count: int = 0
        self.numbered_block_count: int = 0
        self.body_character_count: int = 0
        self.block_character_count: int = 0
        self.low_share_judgment_count: int = 0
        self.character_mismatch_judgment_count: int = 0
        self.low_share_lines: list[str] = []

    def add(self, elitigation_url: str, parsed_judgment: ParsedJudgment) -> None:
        for parsed_block in parsed_judgment.blocks:
            self.kind_to_block_count[parsed_block.kind] += 1
            self.source_style_to_block_count[
                parsed_block.source_style or "(no style)"
            ] += 1
            self.numbered_block_count += parsed_block.printed_number is not None
        details = parsed_judgment.details
        self.empty_field_to_judgment_count["case_name"] += details.case_name is None
        self.empty_field_to_judgment_count["printed_court"] += (
            details.printed_court is None
        )
        self.empty_field_to_judgment_count["printed_case_number"] += (
            details.printed_case_number is None
        )
        self.empty_field_to_judgment_count["printed_coram"] += (
            details.printed_coram is None
        )
        self.empty_field_to_judgment_count["printed_counsel"] += (
            details.printed_counsel is None
        )
        self.empty_field_to_judgment_count["printed_catchwords"] += (
            details.printed_catchwords is None
        )
        self.empty_field_to_judgment_count["printed_decision_date"] += (
            details.printed_decision_date is None
        )
        self.no_decision_date_count += parsed_judgment.decision_date is None
        self.body_character_count += parsed_judgment.body_character_count
        self.block_character_count += parsed_judgment.block_character_count
        self.character_mismatch_judgment_count += (
            parsed_judgment.block_character_count
            != parsed_judgment.body_character_count
        )
        text_share = (
            parsed_judgment.block_character_count / parsed_judgment.body_character_count
        )
        if text_share >= _LOW_TEXT_SHARE:
            return
        self.low_share_judgment_count += 1
        if len(self.low_share_lines) < _MAX_LISTED_LOW_SHARE_JUDGMENTS:
            self.low_share_lines.append(
                f"Low text share {text_share:.2%}: {elitigation_url}"
            )


def _validate_can_commit_judgment(
    session: Session, judgment_id: int, judgment_parse: JudgmentParse
) -> None:
    stored_count = CRUDJudgmentBlock(session).get_count_by_judgment_id(judgment_id)
    planned_count = len(judgment_parse.parsed_judgment.blocks)
    if stored_count != planned_count:
        raise OpenSgLawWriteCheckError(
            f"{stored_count} blocks are stored for {judgment_parse.elitigation_url}, the parse has {planned_count}"
        )


def _log_figures(
    document_count: int,
    superseded_count: int,
    parsed_count: int,
    changed_count: int,
    judgment_figures: _JudgmentFigures,
    unparsed_judgments: list[_UnparsedJudgment],
) -> None:
    logger.info(f"{document_count:,} stored pages read")
    logger.info(f"{superseded_count:,} older bodies of a parsed URL skipped")
    logger.info(f"{parsed_count:,} judgments parsed")
    logger.info(f"{changed_count:,} judgments changed")
    logger.info(f"{parsed_count - changed_count:,} judgments unchanged")
    for block_kind, block_count in sorted(judgment_figures.kind_to_block_count.items()):
        logger.info(f"{block_count:,} blocks of kind {block_kind}")
    for source_style, block_count in judgment_figures.source_style_to_block_count.most_common():
        logger.info(f"{block_count:,} blocks of style {source_style}")
    logger.info(f"{judgment_figures.numbered_block_count:,} blocks with a number")
    for field_name, judgment_count in sorted(
        judgment_figures.empty_field_to_judgment_count.items()
    ):
        logger.info(f"{judgment_count:,} judgments with no {field_name}")
    logger.info(
        f"{judgment_figures.no_decision_date_count:,} judgments with no decision date read"
    )
    if judgment_figures.body_character_count > 0:
        logger.info(
            f"Text share: {judgment_figures.block_character_count / judgment_figures.body_character_count:.2%}"
            " of the body characters land in a block"
        )
    logger.info(
        f"{judgment_figures.low_share_judgment_count:,} judgments under {_LOW_TEXT_SHARE:.0%} text share"
    )
    logger.info(
        f"{judgment_figures.character_mismatch_judgment_count:,} judgments whose block and body character counts differ"
    )
    for low_share_line in judgment_figures.low_share_lines:
        logger.info(low_share_line)
    for unparsed_judgment in unparsed_judgments:
        logger.info(
            f"Unparsed {unparsed_judgment.elitigation_url}: {unparsed_judgment.reason}"
        )
    logger.info(f"{len(unparsed_judgments):,} stored pages unparsed")


def apply_judgments(is_commit: bool) -> None:
    if is_commit:
        validate_can_write(settings.database_url)
    judgment_figures = _JudgmentFigures()
    unparsed_judgments: list[_UnparsedJudgment] = []
    parsed_urls: set[str] = set()
    superseded_count = 0
    changed_count = 0
    with Session(engine) as session:
        document_rows = CRUDSourceResponse(
            session
        ).get_document_rows_by_source_and_kind_and_status_code_and_body_text_not_null_newest_first(
            SourceName.ELITIGATION, ResponseKind.DOCUMENT, _HTTP_OK
        )
        for document_row in document_rows:
            if document_row.requested_url in parsed_urls:
                superseded_count += 1
                continue
            try:
                judgment_parse = get_judgment_parse(session, document_row)
            except OpenSgLawJudgmentParseError as error:
                unparsed_judgments.append(
                    _UnparsedJudgment(document_row.requested_url, str(error))
                )
                continue
            if is_commit and judgment_parse.is_changed:
                try:
                    judgment_id = write_judgment(session, judgment_parse)
                    _validate_can_commit_judgment(session, judgment_id, judgment_parse)
                except OpenSgLawWriteCheckError as error:
                    session.rollback()
                    unparsed_judgments.append(
                        _UnparsedJudgment(document_row.requested_url, str(error))
                    )
                    continue
                session.commit()
            parsed_urls.add(document_row.requested_url)
            changed_count += judgment_parse.is_changed
            judgment_figures.add(
                document_row.requested_url, judgment_parse.parsed_judgment
            )
            if len(parsed_urls) % _PROGRESS_EVERY_JUDGMENTS == 0:
                logger.info(f"{len(parsed_urls):,} judgments parsed so far")
        _log_figures(
            len(document_rows),
            superseded_count,
            len(parsed_urls),
            changed_count,
            judgment_figures,
            unparsed_judgments,
        )
        if not is_commit:
            logger.info("Dry run: nothing written")
            return
        logger.info("Committed")
        vacuum_analyze_written_tables(
            session,
            [
                Judgment.__tablename__,  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
                JudgmentBlock.__tablename__,  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
            ],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse the stored judgment pages into judgments and ordered blocks, or with no --commit log what would change"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="write the judgments now",
    )
    arguments = parser.parse_args()
    apply_judgments(arguments.commit)
