from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from sqlmodel import Session

from crud.act_history_entry import CRUDActHistoryEntry
from crud.bill import CRUDBill
from crud.bill_report import CRUDBillReport
from database.act_history_entry import ActHistoryEntry
from database.bill import Bill
from enums import ActHistoryEntryKind, BillLinkSource
from schemas.act_link_plan import (
    ActLinkPlan,
    PlannedAct,
    PlannedActHistoryEntry,
    PlannedBill,
)
from schemas.hansard_report_export import HansardReportExport, HansardReportExportRow
from tests.document_seed import seed_legislation
from tests.source_seed import seed_sources

ACT_LINK_PLAN_SHA256 = "a" * 64
REPORT_EXPORT_SHA256 = "b" * 64
STORED_SSO_CODES = frozenset({"EDA2025", "WA2026"})


@dataclass(frozen=True)
class StoredLinkCounts:
    bill_count: int
    bill_report_count: int
    history_entry_count: int
    linked_history_entry_count: int


def get_stored_link_counts(session: Session) -> StoredLinkCounts:
    session.expire_all()
    return StoredLinkCounts(
        bill_count=CRUDBill(session).get_count(),
        bill_report_count=CRUDBillReport(session).get_count(),
        history_entry_count=CRUDActHistoryEntry(session).get_count(),
        linked_history_entry_count=CRUDActHistoryEntry(
            session
        ).get_count_by_bill_id_not_null(),
    )


def build_entry(
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


def build_act_link_plan() -> ActLinkPlan:
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
                    build_entry(1, 0, BillLinkSource.FIRST_READING_DATE),
                    build_entry(2, None, None),
                ],
            ),
            PlannedAct(
                sso_code="WA2026",
                title="Water Act 2026",
                entries=[build_entry(1, 1, BillLinkSource.HAND_KEPT)],
            ),
        ],
        unfetched_sso_codes=[],
        unparsed_entries=[],
    )


def build_report_export(report_ids: tuple[int, ...]) -> HansardReportExport:
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


def seed_hansard_link_legislation(session: Session) -> None:
    seed_sources(session)
    seed_legislation(
        session, {"EDA2025": "Estate Duty Act 2025", "WA2026": "Water Act 2026"}
    )


def add_competition_bill_and_history(session: Session, legislation_id: int) -> int:
    bill = Bill(
        title="Competition Bill",
        title_key="competition",
        first_sitting_date=datetime(2004, 9, 1),
        last_sitting_date=datetime(2004, 10, 19),
        is_passed=True,
    )
    CRUDBill(session).add_many([bill])
    assert bill.id is not None
    CRUDActHistoryEntry(session).add_many(
        [
            ActHistoryEntry(
                ordinal=1,
                printed_text="Act 46 of 2004",
                printed_law_number="46",
                printed_title="Competition Act",
                kind=ActHistoryEntryKind.ACT,
                bill_link_source=BillLinkSource.FIRST_READING_DATE,
                legislation_id=legislation_id,
                bill_id=bill.id,
            ),
            ActHistoryEntry(
                ordinal=2,
                printed_text="Revised Edition 2006",
                printed_law_number="",
                printed_title="Competition Act",
                kind=ActHistoryEntryKind.REVISED_EDITION,
                legislation_id=legislation_id,
            ),
        ]
    )
    return bill.id
