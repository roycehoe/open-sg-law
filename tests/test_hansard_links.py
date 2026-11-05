import pytest

from enums import BillLinkSource
from exceptions import OpenSgLawHansardLinkError
from services.hansard_links import build_hansard_link_plan
from tests.hansard_link_seed import (
    ACT_LINK_PLAN_SHA256,
    REPORT_EXPORT_SHA256,
    STORED_SSO_CODES,
    build_act_link_plan,
    build_report_export,
)

_REPORT_COUNT = 3
_ENTRY_COUNT = 3


def test_a_plan_and_an_export_give_the_bills_reports_and_entries() -> None:
    hansard_link_plan = build_hansard_link_plan(
        build_act_link_plan(),
        build_report_export((10, 11, 12, 13)),
        STORED_SSO_CODES,
        ACT_LINK_PLAN_SHA256,
        REPORT_EXPORT_SHA256,
    )

    assert hansard_link_plan.act_link_plan_sha256 == ACT_LINK_PLAN_SHA256
    assert hansard_link_plan.report_export_sha256 == REPORT_EXPORT_SHA256
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
            build_act_link_plan(),
            build_report_export((10, 12)),
            STORED_SSO_CODES,
            ACT_LINK_PLAN_SHA256,
            REPORT_EXPORT_SHA256,
        )


def test_a_plan_sso_code_with_no_legislation_row_raises_naming_it() -> None:
    with pytest.raises(
        OpenSgLawHansardLinkError,
        match=r"1 plan SSO codes have no legislation row, first \['WA2026'\]",
    ):
        build_hansard_link_plan(
            build_act_link_plan(),
            build_report_export((10, 11, 12)),
            frozenset({"EDA2025"}),
            ACT_LINK_PLAN_SHA256,
            REPORT_EXPORT_SHA256,
        )
