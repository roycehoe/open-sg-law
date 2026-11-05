from sqlmodel import Session

from crud.act_history_entry import CRUDActHistoryEntry
from crud.bill import CRUDBill
from crud.bill_report import CRUDBillReport
from crud.legislation import CRUDLegislation
from database.act_history_entry import ActHistoryEntry
from database.bill import Bill, BillReport
from exceptions import OpenSgLawWriteCheckError
from schemas.act_link_plan import ActLinkPlan
from schemas.hansard_link_plan import HansardLinkPlan
from schemas.hansard_report_export import HansardReportExport
from services.hansard_links import build_hansard_link_plan


def get_hansard_link_plan(
    session: Session,
    act_link_plan: ActLinkPlan,
    hansard_report_export: HansardReportExport,
    act_link_plan_sha256: str,
    report_export_sha256: str,
) -> HansardLinkPlan:
    stored_sso_codes = frozenset(
        legislation_row.sso_code
        for legislation_row in CRUDLegislation(session).get_rows()
    )
    return build_hansard_link_plan(
        act_link_plan,
        hansard_report_export,
        stored_sso_codes,
        act_link_plan_sha256,
        report_export_sha256,
    )


def _get_bill_ids(bills: list[Bill]) -> list[int]:
    bill_ids: list[int] = []
    for bill in bills:
        if bill.id is None:
            raise OpenSgLawWriteCheckError(
                f"Bill {bill.title} has no id after it was flushed"
            )
        bill_ids.append(bill.id)
    return bill_ids


def write_hansard_link_plan(
    session: Session, hansard_link_plan: HansardLinkPlan
) -> None:
    CRUDActHistoryEntry(session).delete_all()
    CRUDBillReport(session).delete_all()
    CRUDBill(session).delete_all()

    bills = [
        Bill(
            title=hansard_link_bill.title,
            title_key=hansard_link_bill.title_key,
            first_sitting_date=hansard_link_bill.first_sitting_date,
            last_sitting_date=hansard_link_bill.last_sitting_date,
            is_passed=hansard_link_bill.is_passed,
        )
        for hansard_link_bill in hansard_link_plan.bills
    ]
    CRUDBill(session).add_many(bills)
    bill_ids = _get_bill_ids(bills)

    CRUDBillReport(session).add_many(
        [
            BillReport(
                sprs_report_id=hansard_link_bill_report.sprs_report_id,
                openhansard_url=hansard_link_bill_report.openhansard_url,
                report_type=hansard_link_bill_report.report_type,
                sitting_date=hansard_link_bill_report.sitting_date,
                title=hansard_link_bill_report.title,
                hansard_row_id=hansard_link_bill_report.hansard_row_id,
                bill_id=bill_ids[hansard_link_bill_report.bill_index],
            )
            for hansard_link_bill_report in hansard_link_plan.bill_reports
        ]
    )

    sso_code_to_legislation_id = {
        legislation_row.sso_code: legislation_row.id
        for legislation_row in CRUDLegislation(session).get_rows()
    }
    CRUDActHistoryEntry(session).add_many(
        [
            ActHistoryEntry(
                ordinal=hansard_link_entry.ordinal,
                printed_text=hansard_link_entry.printed_text,
                printed_law_number=hansard_link_entry.printed_law_number,
                printed_title=hansard_link_entry.printed_title,
                printed_bill_number=hansard_link_entry.printed_bill_number,
                first_reading_date=hansard_link_entry.first_reading_date,
                second_reading_date=hansard_link_entry.second_reading_date,
                third_reading_date=hansard_link_entry.third_reading_date,
                commencement_date=hansard_link_entry.commencement_date,
                kind=hansard_link_entry.kind,
                bill_link_source=hansard_link_entry.bill_link_source,
                legislation_id=sso_code_to_legislation_id[hansard_link_entry.sso_code],
                bill_id=(
                    None
                    if hansard_link_entry.bill_index is None
                    else bill_ids[hansard_link_entry.bill_index]
                ),
            )
            for hansard_link_entry in hansard_link_plan.entries
        ]
    )
