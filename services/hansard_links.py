from database.act_history_entry import ActHistoryEntry
from database.bill import Bill, BillReport
from exceptions import OpenSgLawHansardLinkError
from schemas.act_link_plan import ActLinkPlan
from schemas.hansard_link_plan import (
    HansardLinkBill,
    HansardLinkBillReport,
    HansardLinkEntry,
    HansardLinkPlan,
)
from schemas.hansard_report_export import HansardReportExport, HansardReportExportRow
from utils.openhansard_url import get_openhansard_report_url

_LISTED_REPORT_ID_COUNT = 5
_LISTED_SSO_CODE_COUNT = 5


def _validate_can_find_every_report(
    act_link_plan: ActLinkPlan,
    report_id_to_export_row: dict[int, HansardReportExportRow],
) -> None:
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
            f"{len(missing_report_ids):,} plan report ids are missing from the report export, first {missing_report_ids[:_LISTED_REPORT_ID_COUNT]}"
        )


def _validate_can_find_every_act(
    act_link_plan: ActLinkPlan, stored_sso_codes: frozenset[str]
) -> None:
    missing_sso_codes = sorted(
        {planned_act.sso_code for planned_act in act_link_plan.acts} - stored_sso_codes
    )
    if missing_sso_codes:
        raise OpenSgLawHansardLinkError(
            f"{len(missing_sso_codes):,} plan SSO codes have no legislation row, first {missing_sso_codes[:_LISTED_SSO_CODE_COUNT]}"
        )


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
    _validate_can_find_every_report(act_link_plan, report_id_to_export_row)
    _validate_can_find_every_act(act_link_plan, stored_sso_codes)

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


def build_bills(hansard_link_plan: HansardLinkPlan) -> list[Bill]:
    return [
        Bill(
            title=hansard_link_bill.title,
            title_key=hansard_link_bill.title_key,
            first_sitting_date=hansard_link_bill.first_sitting_date,
            last_sitting_date=hansard_link_bill.last_sitting_date,
            is_passed=hansard_link_bill.is_passed,
        )
        for hansard_link_bill in hansard_link_plan.bills
    ]


def build_bill_reports(
    hansard_link_plan: HansardLinkPlan, bill_ids: list[int]
) -> list[BillReport]:
    return [
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


def build_act_history_entries(
    hansard_link_plan: HansardLinkPlan,
    bill_ids: list[int],
    sso_code_to_legislation_id: dict[str, int],
) -> list[ActHistoryEntry]:
    return [
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
