from datetime import date, datetime

import pytest
from pydantic import ValidationError

from enums import ActHistoryDefect, ActHistoryEntryKind, BillLinkSource
from schemas.act_link_plan import (
    ActLinkPlan,
    PlannedAct,
    PlannedActHistoryEntry,
    PlannedBill,
)
from schemas.hansard_report_export import HansardReportExport

_REPORT_EXPORT_JSON = (
    '{"rows": [{"id": 7, "report_id": "00004663-WA.00000937-WA_1#",'
    ' "report_type": "written-answer", "sitting_date": "2020-01-06",'
    ' "title": "Example title"}]}'
)
_REPORT_EXPORT_JSON_WITHOUT_TITLE = (
    '{"rows": [{"id": 7, "report_id": "00004663-WA.00000937-WA_1#",'
    ' "report_type": "written-answer", "sitting_date": "2020-01-06"}]}'
)


def test_an_act_link_plan_round_trips_through_json() -> None:
    act_link_plan = ActLinkPlan(
        bills=[
            PlannedBill(
                title="Example Bill",
                title_key="example",
                first_sitting_date=datetime(2019, 3, 4),
                last_sitting_date=datetime(2019, 5, 6),
                is_passed=True,
                report_ids=[1, 2],
            )
        ],
        skipped_reports=[],
        acts=[
            PlannedAct(
                sso_code="EA2019",
                title="Example Act 2019",
                entries=[
                    PlannedActHistoryEntry(
                        ordinal=1,
                        printed_text="Act 3 of 2019",
                        printed_law_number="3",
                        printed_title="Example Act",
                        printed_bill_number=None,
                        first_reading_date=date(2019, 3, 4),
                        second_reading_date=None,
                        third_reading_date=date(2019, 5, 6),
                        commencement_date=None,
                        kind=ActHistoryEntryKind.ACT,
                        defects=[ActHistoryDefect.MISSING_READING],
                        bill_index=0,
                        bill_link_source=BillLinkSource.FIRST_READING_DATE,
                    )
                ],
            )
        ],
        unfetched_sso_codes=[],
        unparsed_entries=[],
    )

    round_tripped = ActLinkPlan.model_validate_json(act_link_plan.model_dump_json())

    assert round_tripped == act_link_plan


def test_a_report_export_with_one_row_parses() -> None:
    hansard_report_export = HansardReportExport.model_validate_json(_REPORT_EXPORT_JSON)

    assert hansard_report_export.rows[0].sitting_date == date(2020, 1, 6)
    assert hansard_report_export.rows[0].report_id == "00004663-WA.00000937-WA_1#"


def test_a_report_export_row_without_a_title_raises() -> None:
    with pytest.raises(ValidationError):
        HansardReportExport.model_validate_json(_REPORT_EXPORT_JSON_WITHOUT_TITLE)
