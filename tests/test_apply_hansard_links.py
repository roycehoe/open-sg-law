import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

import scripts.apply_hansard_links as apply_hansard_links_script
from crud.act_history_entry import CRUDActHistoryEntry
from crud.bill import CRUDBill
from crud.bill_report import CRUDBillReport
from database.act_history_entry import ActHistoryEntry
from database.bill import Bill
from exceptions import (
    OpenSgLawHansardLinkError,
    OpenSgLawWriteCheckError,
    OpenSgLawWriteTargetError,
)
from schemas.hansard_link_plan import HansardLinkPlan
from schemas.hansard_report_export import HansardReportExport
from scripts.apply_hansard_links import apply_hansard_links
from tests.hansard_link_seed import (
    build_act_link_plan,
    build_report_export,
    seed_legislation,
)

_PROTECTED_DATABASE_URL = "postgresql://u:p@localhost:5435/x"
_FULL_COUNTS = (2, 3, 3, 2)
_NO_ROWS = (0, 0, 0, 0)


class _LogRecorder:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str) -> None:
        self.messages.append(message)


@pytest.fixture
def log_recorder(
    scratch_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> _LogRecorder:
    recorder = _LogRecorder()
    monkeypatch.setattr(apply_hansard_links_script, "engine", scratch_engine)
    monkeypatch.setattr(apply_hansard_links_script, "logger", recorder)
    return recorder


def _write_inputs(
    directory: Path, hansard_report_export: HansardReportExport
) -> tuple[Path, Path, Path]:
    plan_file = directory / "act-links.json"
    report_export_file = directory / "report-export.json"
    plan_file.write_text(build_act_link_plan().model_dump_json())
    report_export_file.write_text(hansard_report_export.model_dump_json())
    return plan_file, report_export_file, directory / "hansard-links.json"


def _get_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get_stored_counts(session: Session) -> tuple[int, int, int, int]:
    session.expire_all()
    return (
        CRUDBill(session).get_count(),
        CRUDBillReport(session).get_count(),
        CRUDActHistoryEntry(session).get_count(),
        CRUDActHistoryEntry(session).get_count_by_bill_id_not_null(),
    )


def _get_stored_contents(session: Session) -> tuple[list[str], list[tuple[int, int]]]:
    session.expire_all()
    bill_titles = list(session.exec(select(Bill.title).order_by(col(Bill.title))).all())
    entries = session.exec(
        select(ActHistoryEntry.legislation_id, ActHistoryEntry.ordinal).order_by(
            col(ActHistoryEntry.legislation_id), col(ActHistoryEntry.ordinal)
        )
    ).all()
    return bill_titles, [
        (legislation_id, ordinal) for legislation_id, ordinal in entries
    ]


def test_dry_run_logs_the_hashes_and_counts_and_writes_the_plan_file_only(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_legislation(scratch_session)
    plan_file, report_export_file, plan_output = _write_inputs(
        tmp_path, build_report_export((10, 11, 12, 13))
    )

    apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=False)

    assert log_recorder.messages == [
        f"Act link plan SHA-256 {_get_sha256(plan_file)}",
        f"Report export SHA-256 {_get_sha256(report_export_file)}",
        "Acts: 2 read",
        "Entries by kind: ACT 3",
        "Bills: 2, 1 passed",
        "Bill reports: 3",
        "Entries linked by rule: FIRST_READING_DATE 1, HAND_KEPT 1",
        "Act and Ordinance entries not linked, by kind and decade of first reading: ACT 2020s 1",
        "Entries by source defect: none",
        "Skipped: 0 reports whose title names no bill, 0 distinct titles",
        "Unfetched SSO codes: 0",
        "Unparsed entries: 0",
        "Dry run: nothing written",
    ]
    hansard_link_plan = HansardLinkPlan.model_validate_json(plan_output.read_text())
    assert hansard_link_plan.act_link_plan_sha256 == _get_sha256(plan_file)
    assert len(hansard_link_plan.bill_reports) == _FULL_COUNTS[1]
    assert _get_stored_counts(scratch_session) == _NO_ROWS


def test_commit_writes_the_reviewed_plan(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_legislation(scratch_session)
    plan_file, report_export_file, plan_output = _write_inputs(
        tmp_path, build_report_export((10, 11, 12))
    )
    apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=False)

    apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=True)

    assert log_recorder.messages[-1] == "Committed"
    assert _get_stored_counts(scratch_session) == _FULL_COUNTS
    assert CRUDBill(scratch_session).get_count_by_is_passed(is_passed=True) == 1


def test_commit_twice_leaves_the_same_rows(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_legislation(scratch_session)
    plan_file, report_export_file, plan_output = _write_inputs(
        tmp_path, build_report_export((10, 11, 12))
    )
    apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=False)
    apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=True)
    stored_contents = _get_stored_contents(scratch_session)

    apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=True)

    assert _get_stored_counts(scratch_session) == _FULL_COUNTS
    assert _get_stored_contents(scratch_session) == stored_contents


def test_commit_refuses_a_plan_that_differs_from_the_reviewed_plan(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_legislation(scratch_session)
    plan_file, report_export_file, plan_output = _write_inputs(
        tmp_path, build_report_export((10, 11, 12))
    )
    apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=False)
    reviewed_plan = json.loads(plan_output.read_text())
    reviewed_plan["bills"][0]["title"] = "Edited Bill"
    plan_output.write_text(json.dumps(reviewed_plan))

    with pytest.raises(
        OpenSgLawWriteCheckError, match="The plan differs from the reviewed plan"
    ):
        apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=True)

    assert _get_stored_counts(scratch_session) == _NO_ROWS


def test_commit_refuses_a_changed_input_file(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_legislation(scratch_session)
    plan_file, report_export_file, plan_output = _write_inputs(
        tmp_path, build_report_export((10, 11, 12))
    )
    apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=False)
    plan_file.write_text(build_act_link_plan().model_dump_json(indent=1))

    with pytest.raises(
        OpenSgLawWriteCheckError, match="The plan differs from the reviewed plan"
    ):
        apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=True)

    assert _get_stored_counts(scratch_session) == _NO_ROWS


def test_a_missing_report_id_is_refused(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_legislation(scratch_session)
    plan_file, report_export_file, plan_output = _write_inputs(
        tmp_path, build_report_export((10, 12))
    )

    with pytest.raises(
        OpenSgLawHansardLinkError, match=r"1 plan report ids are missing"
    ):
        apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=False)

    assert not plan_output.exists()
    assert log_recorder.messages == []


def test_a_missing_sso_code_is_refused(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_legislation(scratch_session)
    plan_file, report_export_file, plan_output = _write_inputs(
        tmp_path, build_report_export((10, 11, 12))
    )
    act_link_plan = build_act_link_plan()
    unknown_act = act_link_plan.acts[1].model_copy(update={"sso_code": "UNKNOWN9"})
    plan_file.write_text(
        act_link_plan.model_copy(
            update={"acts": [act_link_plan.acts[0], unknown_act]}
        ).model_dump_json()
    )

    with pytest.raises(
        OpenSgLawHansardLinkError, match=r"1 plan SSO codes have no legislation row"
    ):
        apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=False)

    assert not plan_output.exists()
    assert log_recorder.messages == []


def test_commit_refuses_the_protected_port_before_any_row_is_written(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_legislation(scratch_session)
    plan_file, report_export_file, plan_output = _write_inputs(
        tmp_path, build_report_export((10, 11, 12))
    )
    apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=False)
    log_recorder.messages.clear()
    monkeypatch.setattr(
        apply_hansard_links_script,
        "settings",
        SimpleNamespace(database_url=_PROTECTED_DATABASE_URL),
    )

    with pytest.raises(OpenSgLawWriteTargetError, match="not 5435"):
        apply_hansard_links(plan_file, report_export_file, plan_output, is_commit=True)

    assert _get_stored_counts(scratch_session) == _NO_ROWS
    assert log_recorder.messages == []
