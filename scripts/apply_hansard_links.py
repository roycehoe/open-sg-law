import argparse
import hashlib
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Optional

from sqlmodel import Session

from crud.act_history_entry import CRUDActHistoryEntry
from crud.bill import CRUDBill
from crud.bill_report import CRUDBillReport
from database.act_history_entry import ActHistoryEntry
from database.bill import Bill, BillReport
from database.init import engine
from enums import ActHistoryEntryKind
from exceptions import OpenSgLawWriteCheckError
from logs import logger
from populate.hansard_links import get_hansard_link_plan, write_hansard_link_plan
from populate.written_tables import vacuum_analyze_written_tables
from schemas.act_link_plan import ActLinkPlan
from schemas.hansard_link_plan import HansardLinkPlan
from schemas.hansard_report_export import HansardReportExport
from settings import settings
from utils.write_target import validate_can_write

_YEARS_PER_DECADE = 10


def _get_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get_decade_label(first_reading_date: Optional[date]) -> str:
    if first_reading_date is None:
        return "no first reading date"
    return f"{first_reading_date.year // _YEARS_PER_DECADE * _YEARS_PER_DECADE}s"


def _format_counts(counts: Counter[str]) -> str:
    return (
        ", ".join(f"{label} {count:,}" for label, count in sorted(counts.items()))
        or "none"
    )


def _log_plan(hansard_link_plan: HansardLinkPlan, act_link_plan: ActLinkPlan) -> None:
    act_link_entries = [
        entry for planned_act in act_link_plan.acts for entry in planned_act.entries
    ]
    skipped_title_count = len(
        {skipped_report.title for skipped_report in act_link_plan.skipped_reports}
    )
    logger.info(f"Act link plan SHA-256 {hansard_link_plan.act_link_plan_sha256}")
    logger.info(f"Report export SHA-256 {hansard_link_plan.report_export_sha256}")
    logger.info(f"Acts: {len(act_link_plan.acts):,} read")
    logger.info(
        f"Entries by kind: {_format_counts(Counter(entry.kind.value for entry in hansard_link_plan.entries))}"
    )
    logger.info(
        f"Bills: {len(hansard_link_plan.bills):,}, {sum(hansard_link_bill.is_passed for hansard_link_bill in hansard_link_plan.bills):,} passed"
    )
    logger.info(f"Bill reports: {len(hansard_link_plan.bill_reports):,}")
    logger.info(
        f"Entries linked by rule: {_format_counts(Counter(entry.bill_link_source.value for entry in hansard_link_plan.entries if entry.bill_link_source is not None))}"
    )
    logger.info(
        f"Act and Ordinance entries not linked, by kind and decade of first reading: {_format_counts(Counter(f'{entry.kind.value} {_get_decade_label(entry.first_reading_date)}' for entry in hansard_link_plan.entries if entry.bill_index is None and (entry.kind == ActHistoryEntryKind.ACT or entry.kind == ActHistoryEntryKind.ORDINANCE)))}"
    )
    logger.info(
        f"Entries by source defect: {_format_counts(Counter(defect.value for entry in act_link_entries for defect in entry.defects))}"
    )
    logger.info(
        f"Skipped: {len(act_link_plan.skipped_reports):,} reports whose title names no bill, {skipped_title_count:,} distinct titles"
    )
    logger.info(f"Unfetched SSO codes: {len(act_link_plan.unfetched_sso_codes):,}")
    logger.info(f"Unparsed entries: {len(act_link_plan.unparsed_entries):,}")
    for unparsed_entry in act_link_plan.unparsed_entries:
        logger.info(f"Unparsed: {unparsed_entry.message}")


def _validate_can_commit_hansard_links(
    session: Session, hansard_link_plan: HansardLinkPlan
) -> None:
    stored_and_planned_counts = {
        "bills": (
            CRUDBill(session).get_count(),
            len(hansard_link_plan.bills),
        ),
        "passed bills": (
            CRUDBill(session).get_count_by_is_passed(is_passed=True),
            sum(
                hansard_link_bill.is_passed
                for hansard_link_bill in hansard_link_plan.bills
            ),
        ),
        "bill reports": (
            CRUDBillReport(session).get_count(),
            len(hansard_link_plan.bill_reports),
        ),
        "act history entries": (
            CRUDActHistoryEntry(session).get_count(),
            len(hansard_link_plan.entries),
        ),
        "linked act history entries": (
            CRUDActHistoryEntry(session).get_count_by_bill_id_not_null(),
            sum(entry.bill_index is not None for entry in hansard_link_plan.entries),
        ),
    }
    for label, (stored_count, planned_count) in stored_and_planned_counts.items():
        if stored_count != planned_count:
            raise OpenSgLawWriteCheckError(
                f"{stored_count} {label} are stored, the plan has {planned_count}"
            )


def apply_hansard_links(
    plan_file: Path,
    report_export_file: Path,
    plan_output: Path,
    is_commit: bool,
) -> None:
    act_link_plan = ActLinkPlan.model_validate_json(plan_file.read_text())
    hansard_report_export = HansardReportExport.model_validate_json(
        report_export_file.read_text()
    )
    act_link_plan_sha256 = _get_sha256(plan_file)
    report_export_sha256 = _get_sha256(report_export_file)
    if not is_commit:
        with Session(engine) as session:
            hansard_link_plan = get_hansard_link_plan(
                session,
                act_link_plan,
                hansard_report_export,
                act_link_plan_sha256,
                report_export_sha256,
            )
        _log_plan(hansard_link_plan, act_link_plan)
        plan_output.write_text(hansard_link_plan.model_dump_json(indent=1))
        logger.info("Dry run: nothing written")
        return

    validate_can_write(settings.database_url)
    reviewed_plan = HansardLinkPlan.model_validate_json(plan_output.read_text())
    with Session(engine) as session:
        hansard_link_plan = get_hansard_link_plan(
            session,
            act_link_plan,
            hansard_report_export,
            act_link_plan_sha256,
            report_export_sha256,
        )
        _log_plan(hansard_link_plan, act_link_plan)
        if hansard_link_plan != reviewed_plan:
            raise OpenSgLawWriteCheckError("The plan differs from the reviewed plan")
        write_hansard_link_plan(session, hansard_link_plan)
        _validate_can_commit_hansard_links(session, hansard_link_plan)
        session.commit()
        logger.info("Committed")
        vacuum_analyze_written_tables(
            session,
            [
                Bill.__tablename__,  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
                BillReport.__tablename__,  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
                ActHistoryEntry.__tablename__,  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
            ],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Store the bills, their reports and the links from Act history entries to bills, checked against a reviewed plan"
    )
    parser.add_argument(
        "--plan-file",
        type=Path,
        required=True,
        help="the act-links plan, kept outside git",
    )
    parser.add_argument(
        "--report-export-file",
        type=Path,
        required=True,
        help="the Hansard report export, kept outside git",
    )
    parser.add_argument(
        "--plan-output",
        type=Path,
        required=True,
        help="the Hansard link plan: written by a dry run, read by --commit",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="check the plan is unchanged, then replace the stored rows with it",
    )
    arguments = parser.parse_args()
    apply_hansard_links(
        arguments.plan_file,
        arguments.report_export_file,
        arguments.plan_output,
        arguments.commit,
    )
