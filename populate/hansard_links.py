from sqlmodel import Session

from crud.act_history_entry import CRUDActHistoryEntry
from crud.bill import CRUDBill
from crud.bill_report import CRUDBillReport
from crud.legislation import CRUDLegislation
from database.bill import Bill
from exceptions import OpenSgLawWriteCheckError
from schemas.act_link_plan import ActLinkPlan
from schemas.hansard_link_plan import HansardLinkPlan
from schemas.hansard_report_export import HansardReportExport
from services.hansard_links import (
    build_act_history_entries,
    build_bill_reports,
    build_bills,
    build_hansard_link_plan,
)


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

    bills = build_bills(hansard_link_plan)
    CRUDBill(session).add_many(bills)
    bill_ids = _get_bill_ids(bills)

    CRUDBillReport(session).add_many(build_bill_reports(hansard_link_plan, bill_ids))

    sso_code_to_legislation_id = {
        legislation_row.sso_code: legislation_row.id
        for legislation_row in CRUDLegislation(session).get_rows()
    }
    CRUDActHistoryEntry(session).add_many(
        build_act_history_entries(
            hansard_link_plan, bill_ids, sso_code_to_legislation_id
        )
    )
