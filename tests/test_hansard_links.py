from datetime import date, datetime
from typing import Optional

import pytest

from enums import ActHistoryEntryKind, BillLinkSource
from exceptions import OpenSgLawHansardLinkError
from schemas.act_link_plan import (
    ActLinkPlan,
    PlannedAct,
    PlannedActHistoryEntry,
    PlannedBill,
)
from schemas.hansard_report_export import HansardReportExport, HansardReportExportRow
from services.hansard_links import build_hansard_link_plan

_ACT_LINK_PLAN_SHA256 = "a" * 64
_REPORT_EXPORT_SHA256 = "b" * 64
_STORED_SSO_CODES = frozenset({"EDA2025", "WA2026"})
_REPORT_COUNT = 3
_ENTRY_COUNT = 3


def _build_entry(
    ordinal: int,
    bill_index: Optional[int],
    bill_link_source: Optional[BillLinkSource],
) -> PlannedActHistoryEntry:
    return PlannedActHistoryEntry(
        ordinal=ordinal,
        printed_text=f"Act {ordinal} of 2025",
        printed_law_number=str(ordinal),
        printed_title="Estate Duty Act",
        printed_bill_number=None,
        first_reading_date=date(2024, 12, 2),
        second_reading_date=None,
        third_reading_date=date(2025, 1, 15),
        commencement_date=None,
        kind=ActHistoryEntryKind.ACT,
        defects=[],
        bill_index=bill_index,
        bill_link_source=bill_link_source,
    )


def _build_act_link_plan() -> ActLinkPlan:
    return ActLinkPlan(
        bills=[
            PlannedBill(
                title="Estate Duty Bill",
                title_key="estatedutybill",
                first_sitting_date=datetime(2024, 12, 2),
                last_sitting_date=datetime(2025, 1, 15),
                is_passed=True,
                report_ids=[10, 11],
            ),
            PlannedBill(
                title="Water Bill",
                title_key="waterbill",
                first_sitting_date=datetime(2026, 3, 3),
                last_sitting_date=datetime(2026, 3, 3),
                is_passed=False,
                report_ids=[12],
            ),
        ],
        skipped_reports=[],
        acts=[
            PlannedAct(
                sso_code="EDA2025",
                title="Estate Duty Act 2025",
                entries=[
                    _build_entry(1, 0, BillLinkSource.FIRST_READING_DATE),
                    _build_entry(2, None, None),
                ],
            ),
            PlannedAct(
                sso_code="WA2026",
                title="Water Act 2026",
                entries=[_build_entry(1, 1, BillLinkSource.HAND_KEPT)],
            ),
        ],
        unfetched_sso_codes=[],
        unparsed_entries=[],
    )


def _build_export(report_ids: tuple[int, ...]) -> HansardReportExport:
    return HansardReportExport(
        rows=[
            HansardReportExportRow(
                id=report_id,
                report_id=f"0000{report_id}-BL.0000{report_id}-BL_1#",
                report_type="bill",
                sitting_date=date(2025, 1, 15),
                title=f"Report {report_id}",
            )
            for report_id in report_ids
        ]
    )


def test_a_plan_and_an_export_give_the_bills_reports_and_entries() -> None:
    hansard_link_plan = build_hansard_link_plan(
        _build_act_link_plan(),
        _build_export((10, 11, 12, 13)),
        _STORED_SSO_CODES,
        _ACT_LINK_PLAN_SHA256,
        _REPORT_EXPORT_SHA256,
    )

    assert hansard_link_plan.act_link_plan_sha256 == _ACT_LINK_PLAN_SHA256
    assert hansard_link_plan.report_export_sha256 == _REPORT_EXPORT_SHA256
    assert [
        hansard_link_bill.title_key for hansard_link_bill in hansard_link_plan.bills
    ] == [
        "estatedutybill",
        "waterbill",
    ]
    assert len(hansard_link_plan.bill_reports) == _REPORT_COUNT
    assert [
        (bill_report.bill_index, bill_report.hansard_row_id)
        for bill_report in hansard_link_plan.bill_reports
    ] == [(0, 10), (0, 11), (1, 12)]
    assert hansard_link_plan.bill_reports[0].sprs_report_id == "000010-BL.000010-BL_1#"
    assert (
        hansard_link_plan.bill_reports[0].openhansard_url
        == "https://openhansard.sg/reports/000010-BL.000010-BL_1"
    )
    assert hansard_link_plan.bill_reports[0].title == "Report 10"
    assert len(hansard_link_plan.entries) == _ENTRY_COUNT
    assert [
        (entry.sso_code, entry.ordinal, entry.bill_index, entry.bill_link_source)
        for entry in hansard_link_plan.entries
    ] == [
        ("EDA2025", 1, 0, BillLinkSource.FIRST_READING_DATE),
        ("EDA2025", 2, None, None),
        ("WA2026", 1, 1, BillLinkSource.HAND_KEPT),
    ]
    assert hansard_link_plan.entries[0].printed_text == "Act 1 of 2025"


def test_a_plan_report_id_missing_from_the_export_raises_naming_it() -> None:
    with pytest.raises(
        OpenSgLawHansardLinkError,
        match=r"1 plan report ids are missing from the report export, first \[11\]",
    ):
        build_hansard_link_plan(
            _build_act_link_plan(),
            _build_export((10, 12)),
            _STORED_SSO_CODES,
            _ACT_LINK_PLAN_SHA256,
            _REPORT_EXPORT_SHA256,
        )


def test_a_plan_sso_code_with_no_legislation_row_raises_naming_it() -> None:
    with pytest.raises(
        OpenSgLawHansardLinkError,
        match=r"1 plan SSO codes have no legislation row, first \['WA2026'\]",
    ):
        build_hansard_link_plan(
            _build_act_link_plan(),
            _build_export((10, 11, 12)),
            frozenset({"EDA2025"}),
            _ACT_LINK_PLAN_SHA256,
            _REPORT_EXPORT_SHA256,
        )
