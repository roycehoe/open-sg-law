from datetime import date

from pydantic import BaseModel, ConfigDict


class HansardReportExportRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    report_id: str
    report_type: str
    sitting_date: date
    title: str


class HansardReportExport(BaseModel):
    model_config = ConfigDict(frozen=True)

    rows: list[HansardReportExportRow]
