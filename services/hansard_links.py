from exceptions import OpenSgLawHansardLinkError
from schemas.act_link_plan import ActLinkPlan
from schemas.hansard_link_plan import (
    HansardLinkBill,
    HansardLinkBillReport,
    HansardLinkEntry,
    HansardLinkPlan,
)
from schemas.hansard_report_export import HansardReportExport
from utils.openhansard_url import get_openhansard_report_url

_LISTED_ID_COUNT = 5


def build_hansard_link_plan(
    act_link_plan: ActLinkPlan,
    hansard_report_export: HansardReportExport,
    stored_sso_codes: frozenset[str],
    act_link_plan_sha256: str,
    report_export_sha256: str,
) -> HansardLinkPlan:
    report_id_to_export_row = {
        export_row.id: export_row for export_row in hansard_report_export.rows
    }
    missing_report_ids = sorted(
        {
            report_id
            for planned_bill in act_link_plan.bills
            for report_id in planned_bill.report_ids
        }
        - report_id_to_export_row.keys()
    )
    if missing_report_ids:
        raise OpenSgLawHansardLinkError(
            f"{len(missing_report_ids):,} plan report ids are missing from the report export, first {missing_report_ids[:_LISTED_ID_COUNT]}"
        )

    missing_sso_codes = sorted(
        {planned_act.sso_code for planned_act in act_link_plan.acts} - stored_sso_codes
    )
    if missing_sso_codes:
        raise OpenSgLawHansardLinkError(
            f"{len(missing_sso_codes):,} plan SSO codes have no legislation row, first {missing_sso_codes[:_LISTED_ID_COUNT]}"
        )

    bill_reports: list[HansardLinkBillReport] = []
    for bill_index, planned_bill in enumerate(act_link_plan.bills):
        for report_id in planned_bill.report_ids:
            export_row = report_id_to_export_row[report_id]
            bill_reports.append(
                HansardLinkBillReport(
                    bill_index=bill_index,
                    sprs_report_id=export_row.report_id,
                    openhansard_url=get_openhansard_report_url(export_row.report_id),
                    report_type=export_row.report_type,
                    sitting_date=export_row.sitting_date,
                    title=export_row.title,
                    hansard_row_id=export_row.id,
                )
            )

    return HansardLinkPlan(
        act_link_plan_sha256=act_link_plan_sha256,
        report_export_sha256=report_export_sha256,
        bills=[
            HansardLinkBill(
                title=planned_bill.title,
                title_key=planned_bill.title_key,
                first_sitting_date=planned_bill.first_sitting_date,
                last_sitting_date=planned_bill.last_sitting_date,
                is_passed=planned_bill.is_passed,
            )
            for planned_bill in act_link_plan.bills
        ],
        bill_reports=bill_reports,
        entries=[
            HansardLinkEntry(
                sso_code=planned_act.sso_code,
                ordinal=entry.ordinal,
                printed_text=entry.printed_text,
                printed_law_number=entry.printed_law_number,
                printed_title=entry.printed_title,
                printed_bill_number=entry.printed_bill_number,
                first_reading_date=entry.first_reading_date,
                second_reading_date=entry.second_reading_date,
                third_reading_date=entry.third_reading_date,
                commencement_date=entry.commencement_date,
                kind=entry.kind,
                bill_index=entry.bill_index,
                bill_link_source=entry.bill_link_source,
            )
            for planned_act in act_link_plan.acts
            for entry in planned_act.entries
        ],
    )
