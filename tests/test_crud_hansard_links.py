from datetime import date

from sqlmodel import Session, col, select

from crud.act_history_entry import CRUDActHistoryEntry
from crud.bill import CRUDBill
from crud.bill_report import CRUDBillReport
from database.bill import BillReport
from database.legislation import Legislation
from tests.document_seed import seed_legislation
from tests.hansard_link_seed import add_competition_bill_and_history
from tests.source_seed import seed_sources

_ENTRY_COUNT = 2
_LINKED_ENTRY_COUNT = 1


def _add_linked_rows(session: Session) -> None:
    seed_sources(session)
    seed_legislation(session, {"TCA2005": "Trade Competition Act 2005"})
    legislation_id = session.exec(select(Legislation.id)).one()
    assert legislation_id is not None
    bill_id = add_competition_bill_and_history(session, legislation_id)
    CRUDBillReport(session).add_many(
        [
            BillReport(
                sprs_report_id="00004663-WA.00000937-WA_1#",
                openhansard_url="https://openhansard.sg/reports/00004663-WA.00000937-WA_1",
                report_type="written-answer",
                sitting_date=date(2004, 10, 19),
                title="Competition Bill",
                hansard_row_id=7,
                bill_id=bill_id,
            )
        ]
    )
    session.commit()


def test_the_counts_follow_what_was_added(scratch_session: Session) -> None:
    _add_linked_rows(scratch_session)

    assert CRUDBill(scratch_session).get_count() == 1
    assert CRUDBill(scratch_session).get_count_by_is_passed(True) == 1
    assert CRUDBill(scratch_session).get_count_by_is_passed(False) == 0
    assert CRUDBillReport(scratch_session).get_count() == 1
    assert CRUDActHistoryEntry(scratch_session).get_count() == _ENTRY_COUNT
    assert (
        CRUDActHistoryEntry(scratch_session).get_count_by_bill_id_not_null()
        == _LINKED_ENTRY_COUNT
    )


def test_delete_all_in_foreign_key_order_leaves_the_tables_empty(
    scratch_session: Session,
) -> None:
    _add_linked_rows(scratch_session)

    CRUDActHistoryEntry(scratch_session).delete_all()
    CRUDBillReport(scratch_session).delete_all()
    CRUDBill(scratch_session).delete_all()
    scratch_session.commit()

    assert CRUDActHistoryEntry(scratch_session).get_count() == 0
    assert CRUDBillReport(scratch_session).get_count() == 0
    assert CRUDBill(scratch_session).get_count() == 0
    legislation_ids = scratch_session.exec(
        select(Legislation.id).order_by(col(Legislation.id))
    ).all()
    assert len(legislation_ids) == 1
