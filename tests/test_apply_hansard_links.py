import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import Session, col, select

import scripts.apply_hansard_links as apply_hansard_links_script
from crud.bill import CRUDBill
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
    StoredLinkCounts,
    build_act_link_plan,
    build_report_export,
    get_stored_link_counts,
    seed_hansard_link_legislation,
)

_PROTECTED_DATABASE_URL = "postgresql://u:p@localhost:5435/x"
_FULL_COUNTS = StoredLinkCounts(
    bill_count=2,
    bill_report_count=3,
    history_entry_count=3,
    linked_history_entry_count=2,
)
_NO_ROWS = StoredLinkCounts(
    bill_count=0,
    bill_report_count=0,
    history_entry_count=0,
    linked_history_entry_count=0,
)


class _LogRecorder:
    def __init__(self):
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


@dataclass(frozen=True)
class _InputFiles:
    plan_file: Path
    report_export_file: Path
    plan_output: Path


def _write_inputs(
    directory: Path, hansard_report_export: HansardReportExport
) -> _InputFiles:
    plan_file = directory / "act-links.json"
    report_export_file = directory / "report-export.json"
    plan_file.write_text(build_act_link_plan().model_dump_json())
    report_export_file.write_text(hansard_report_export.model_dump_json())
    return _InputFiles(
        plan_file=plan_file,
        report_export_file=report_export_file,
        plan_output=directory / "hansard-links.json",
    )


def _get_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class _HistoryEntryKey:
    legislation_id: int
    ordinal: int


def _get_bill_titles(session: Session) -> list[str]:
    session.expire_all()
    return list(session.exec(select(Bill.title).order_by(col(Bill.title))).all())


def _get_history_entry_keys(session: Session) -> list[_HistoryEntryKey]:
    session.expire_all()
    entries = session.exec(
        select(ActHistoryEntry.legislation_id, ActHistoryEntry.ordinal).order_by(
            col(ActHistoryEntry.legislation_id), col(ActHistoryEntry.ordinal)
        )
    ).all()
    return [
        _HistoryEntryKey(legislation_id=legislation_id, ordinal=ordinal)
        for legislation_id, ordinal in entries
    ]


def test_dry_run_logs_the_hashes_and_counts_and_writes_the_plan_file_only(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_hansard_link_legislation(scratch_session)
    input_files = _write_inputs(tmp_path, build_report_export((10, 11, 12, 13)))

    apply_hansard_links(
        input_files.plan_file,
        input_files.report_export_file,
        input_files.plan_output,
        is_commit=False,
    )

    assert log_recorder.messages == [
        f"Act link plan SHA-256 {_get_sha256(input_files.plan_file)}",
        f"Report export SHA-256 {_get_sha256(input_files.report_export_file)}",
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
    hansard_link_plan = HansardLinkPlan.model_validate_json(
        input_files.plan_output.read_text()
    )
    assert hansard_link_plan.act_link_plan_sha256 == _get_sha256(input_files.plan_file)
    assert len(hansard_link_plan.bill_reports) == _FULL_COUNTS.bill_report_count
    assert get_stored_link_counts(scratch_session) == _NO_ROWS


def test_commit_writes_the_reviewed_plan(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_hansard_link_legislation(scratch_session)
    input_files = _write_inputs(tmp_path, build_report_export((10, 11, 12)))
    apply_hansard_links(
        input_files.plan_file,
        input_files.report_export_file,
        input_files.plan_output,
        is_commit=False,
    )

    apply_hansard_links(
        input_files.plan_file,
        input_files.report_export_file,
        input_files.plan_output,
        is_commit=True,
    )

    assert log_recorder.messages[-1] == "Committed"
    assert get_stored_link_counts(scratch_session) == _FULL_COUNTS
    assert CRUDBill(scratch_session).get_count_by_is_passed(is_passed=True) == 1


def test_commit_twice_leaves_the_same_rows(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_hansard_link_legislation(scratch_session)
    input_files = _write_inputs(tmp_path, build_report_export((10, 11, 12)))
    apply_hansard_links(
        input_files.plan_file,
        input_files.report_export_file,
        input_files.plan_output,
        is_commit=False,
    )
    apply_hansard_links(
        input_files.plan_file,
        input_files.report_export_file,
        input_files.plan_output,
        is_commit=True,
    )
    bill_titles = _get_bill_titles(scratch_session)
    history_entry_keys = _get_history_entry_keys(scratch_session)

    apply_hansard_links(
        input_files.plan_file,
        input_files.report_export_file,
        input_files.plan_output,
        is_commit=True,
    )

    assert get_stored_link_counts(scratch_session) == _FULL_COUNTS
    assert _get_bill_titles(scratch_session) == bill_titles
    assert _get_history_entry_keys(scratch_session) == history_entry_keys


def test_commit_refuses_a_plan_that_differs_from_the_reviewed_plan(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_hansard_link_legislation(scratch_session)
    input_files = _write_inputs(tmp_path, build_report_export((10, 11, 12)))
    apply_hansard_links(
        input_files.plan_file,
        input_files.report_export_file,
        input_files.plan_output,
        is_commit=False,
    )
    reviewed_plan = json.loads(input_files.plan_output.read_text())
    reviewed_plan["bills"][0]["title"] = "Edited Bill"
    input_files.plan_output.write_text(json.dumps(reviewed_plan))

    with pytest.raises(
        OpenSgLawWriteCheckError, match="The plan differs from the reviewed plan"
    ):
        apply_hansard_links(
            input_files.plan_file,
            input_files.report_export_file,
            input_files.plan_output,
            is_commit=True,
        )

    assert get_stored_link_counts(scratch_session) == _NO_ROWS


def test_commit_refuses_a_changed_input_file(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_hansard_link_legislation(scratch_session)
    input_files = _write_inputs(tmp_path, build_report_export((10, 11, 12)))
    apply_hansard_links(
        input_files.plan_file,
        input_files.report_export_file,
        input_files.plan_output,
        is_commit=False,
    )
    input_files.plan_file.write_text(build_act_link_plan().model_dump_json(indent=1))

    with pytest.raises(
        OpenSgLawWriteCheckError, match="The plan differs from the reviewed plan"
    ):
        apply_hansard_links(
            input_files.plan_file,
            input_files.report_export_file,
            input_files.plan_output,
            is_commit=True,
        )

    assert get_stored_link_counts(scratch_session) == _NO_ROWS


def test_a_missing_report_id_is_refused(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_hansard_link_legislation(scratch_session)
    input_files = _write_inputs(tmp_path, build_report_export((10, 12)))

    with pytest.raises(
        OpenSgLawHansardLinkError, match=r"1 plan report ids are missing"
    ):
        apply_hansard_links(
            input_files.plan_file,
            input_files.report_export_file,
            input_files.plan_output,
            is_commit=False,
        )

    assert not input_files.plan_output.exists()
    assert log_recorder.messages == []


def test_a_missing_sso_code_is_refused(
    scratch_session: Session, log_recorder: _LogRecorder, tmp_path: Path
) -> None:
    seed_hansard_link_legislation(scratch_session)
    input_files = _write_inputs(tmp_path, build_report_export((10, 11, 12)))
    act_link_plan = build_act_link_plan()
    unknown_act = act_link_plan.acts[1].model_copy(update={"sso_code": "UNKNOWN9"})
    input_files.plan_file.write_text(
        act_link_plan.model_copy(
            update={"acts": [act_link_plan.acts[0], unknown_act]}
        ).model_dump_json()
    )

    with pytest.raises(
        OpenSgLawHansardLinkError, match=r"1 plan SSO codes have no legislation row"
    ):
        apply_hansard_links(
            input_files.plan_file,
            input_files.report_export_file,
            input_files.plan_output,
            is_commit=False,
        )

    assert not input_files.plan_output.exists()
    assert log_recorder.messages == []


def test_commit_refuses_the_protected_port_before_any_row_is_written(
    scratch_session: Session,
    log_recorder: _LogRecorder,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed_hansard_link_legislation(scratch_session)
    input_files = _write_inputs(tmp_path, build_report_export((10, 11, 12)))
    apply_hansard_links(
        input_files.plan_file,
        input_files.report_export_file,
        input_files.plan_output,
        is_commit=False,
    )
    log_recorder.messages.clear()
    monkeypatch.setattr(
        apply_hansard_links_script,
        "settings",
        SimpleNamespace(database_url=_PROTECTED_DATABASE_URL),
    )

    with pytest.raises(OpenSgLawWriteTargetError, match="not 5435"):
        apply_hansard_links(
            input_files.plan_file,
            input_files.report_export_file,
            input_files.plan_output,
            is_commit=True,
        )

    assert get_stored_link_counts(scratch_session) == _NO_ROWS
    assert log_recorder.messages == []
