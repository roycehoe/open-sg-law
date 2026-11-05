from datetime import date, datetime

from sqlmodel import Session, col, select

from crud.act_history_entry import CRUDActHistoryEntry
from crud.bill import CRUDBill
from crud.bill_report import CRUDBillReport
from database.act_history_entry import ActHistoryEntry
from database.bill import Bill, BillReport
from database.legislation import Legislation
from enums import ActHistoryEntryKind, BillLinkSource, SourceName
from tests.source_seed import seed_sources

_ENTRY_COUNT = 2
_LINKED_ENTRY_COUNT = 1


def _add_linked_rows(session: Session) -> None:
    seed_sources(session)
    legislation = Legislation(
        sso_code="TCA2005",
        title="Trade Competition Act 2005",
        is_in_newest_listing=True,
        listing_source=SourceName.SSO,
    )
    session.add(legislation)
    session.flush()
    bill = Bill(
        title="Competition Bill",
        title_key="competition",
        first_sitting_date=datetime(2004, 9, 1),
        last_sitting_date=datetime(2004, 10, 19),
        is_passed=True,
    )
    CRUDBill(session).add_many([bill])
    assert legislation.id is not None
    assert bill.id is not None
    CRUDBillReport(session).add_many(
        [
            BillReport(
                sprs_report_id="00004663-WA.00000937-WA_1#",
                openhansard_url="https://openhansard.sg/reports/00004663-WA.00000937-WA_1",
                report_type="written-answer",
                sitting_date=date(2004, 10, 19),
                title="Competition Bill",
                hansard_row_id=7,
                bill_id=bill.id,
            )
        ]
    )
    CRUDActHistoryEntry(session).add_many(
        [
            ActHistoryEntry(
                ordinal=1,
                printed_text="Act 46 of 2004",
                printed_law_number="46",
                printed_title="Competition Act",
                kind=ActHistoryEntryKind.ACT,
                bill_link_source=BillLinkSource.FIRST_READING_DATE,
                legislation_id=legislation.id,
                bill_id=bill.id,
            ),
            ActHistoryEntry(
                ordinal=2,
                printed_text="Revised Edition 2006",
                printed_law_number="",
                printed_title="Competition Act",
                kind=ActHistoryEntryKind.REVISED_EDITION,
                legislation_id=legislation.id,
            ),
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
