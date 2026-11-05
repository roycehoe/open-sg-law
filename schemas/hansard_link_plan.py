from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from enums import ActHistoryEntryKind, BillLinkSource


class HansardLinkBill(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    title_key: str
    first_sitting_date: datetime
    last_sitting_date: datetime
    is_passed: bool


class HansardLinkBillReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    bill_index: int
    sprs_report_id: str
    openhansard_url: str
    report_type: str
    sitting_date: date
    title: str
    hansard_row_id: int


class HansardLinkEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    sso_code: str
    ordinal: int
    printed_text: str
    printed_law_number: str
    printed_title: str
    printed_bill_number: Optional[str]
    first_reading_date: Optional[date]
    second_reading_date: Optional[date]
    third_reading_date: Optional[date]
    commencement_date: Optional[date]
    kind: ActHistoryEntryKind
    bill_index: Optional[int]
    bill_link_source: Optional[BillLinkSource]


class HansardLinkPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    act_link_plan_sha256: str
    report_export_sha256: str
    bills: list[HansardLinkBill]
    bill_reports: list[HansardLinkBillReport]
    entries: list[HansardLinkEntry]
