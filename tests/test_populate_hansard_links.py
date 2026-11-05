import pytest
from sqlmodel import Session, col, select

from crud.bill_report import CRUDBillReport
from database.act_history_entry import ActHistoryEntry
from database.bill import Bill
from exceptions import OpenSgLawWriteCheckError
from populate.hansard_links import get_hansard_link_plan, write_hansard_link_plan
from schemas.hansard_link_plan import HansardLinkPlan
from tests.hansard_link_seed import (
    ACT_LINK_PLAN_SHA256,
    REPORT_EXPORT_SHA256,
    StoredLinkCounts,
    build_act_link_plan,
    build_report_export,
    get_stored_link_counts,
    seed_hansard_link_legislation,
)

_FULL_COUNTS = StoredLinkCounts(
    bill_count=2,
    bill_report_count=3,
    history_entry_count=3,
    linked_history_entry_count=2,
)
_CHANGED_COUNTS = StoredLinkCounts(
    bill_count=1,
    bill_report_count=2,
    history_entry_count=2,
    linked_history_entry_count=1,
)


def _get_plan(session: Session) -> HansardLinkPlan:
    return get_hansard_link_plan(
        session,
        build_act_link_plan(),
        build_report_export((10, 11, 12)),
        ACT_LINK_PLAN_SHA256,
        REPORT_EXPORT_SHA256,
    )


def _get_changed_plan(hansard_link_plan: HansardLinkPlan) -> HansardLinkPlan:
    return hansard_link_plan.model_copy(
        update={
            "bills": hansard_link_plan.bills[:1],
            "bill_reports": hansard_link_plan.bill_reports[:2],
            "entries": hansard_link_plan.entries[:2],
        }
    )


def _get_bill_ids(session: Session) -> list[int]:
    statement = select(Bill.id).order_by(col(Bill.id))
    return [bill_id for bill_id in session.exec(statement).all() if bill_id is not None]


def test_the_plan_reads_the_stored_sso_codes(scratch_session: Session) -> None:
    seed_hansard_link_legislation(scratch_session)

    hansard_link_plan = _get_plan(scratch_session)

    assert len(hansard_link_plan.bills) == _FULL_COUNTS.bill_count
    assert len(hansard_link_plan.entries) == _FULL_COUNTS.history_entry_count


def test_writing_a_plan_stores_its_rows_with_the_links(
    scratch_session: Session,
) -> None:
    seed_hansard_link_legislation(scratch_session)

    write_hansard_link_plan(scratch_session, _get_plan(scratch_session))
    scratch_session.commit()

    assert get_stored_link_counts(scratch_session) == _FULL_COUNTS
    entries = scratch_session.exec(
        select(ActHistoryEntry).order_by(
            col(ActHistoryEntry.legislation_id), col(ActHistoryEntry.ordinal)
        )
    ).all()
    bill_ids = _get_bill_ids(scratch_session)
    assert [
        (entry.legislation_id, entry.ordinal, entry.bill_id) for entry in entries
    ] == [(1, 1, bill_ids[0]), (1, 2, None), (2, 1, bill_ids[1])]


def test_writing_a_changed_plan_replaces_every_row(scratch_session: Session) -> None:
    seed_hansard_link_legislation(scratch_session)
    hansard_link_plan = _get_plan(scratch_session)
    write_hansard_link_plan(scratch_session, hansard_link_plan)
    scratch_session.commit()
    earlier_bill_ids = _get_bill_ids(scratch_session)

    write_hansard_link_plan(scratch_session, _get_changed_plan(hansard_link_plan))
    scratch_session.commit()

    assert get_stored_link_counts(scratch_session) == _CHANGED_COUNTS
    assert set(_get_bill_ids(scratch_session)).isdisjoint(earlier_bill_ids)


def test_a_failure_after_the_delete_leaves_the_earlier_rows_after_a_rollback(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_hansard_link_legislation(scratch_session)
    hansard_link_plan = _get_plan(scratch_session)
    write_hansard_link_plan(scratch_session, hansard_link_plan)
    scratch_session.commit()

    def fail_to_add(self: CRUDBillReport, bill_reports: list) -> None:
        raise OpenSgLawWriteCheckError("write failed")

    monkeypatch.setattr(CRUDBillReport, "add_many", fail_to_add)

    with pytest.raises(OpenSgLawWriteCheckError, match="write failed"):
        write_hansard_link_plan(scratch_session, _get_changed_plan(hansard_link_plan))
    scratch_session.rollback()

    assert get_stored_link_counts(scratch_session) == _FULL_COUNTS
