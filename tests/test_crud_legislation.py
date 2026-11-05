from sqlmodel import Session

from crud.legislation import CRUDLegislation, LegislationRow
from database.legislation import Legislation
from enums import SourceName
from tests.source_seed import seed_sources
from utils.legislation_update import LegislationUpdate

_TITLE_TCA = "Trade Competition Act 2005"
_TITLE_AA = "Arbitration Act 2001"
_LEGISLATION_COUNT = 2


def _add_two_legislations(session: Session) -> None:
    seed_sources(session)
    CRUDLegislation(session).add_many(
        [
            Legislation(
                sso_code="TCA2005",
                title=_TITLE_TCA,
                is_in_newest_listing=True,
                listing_source=SourceName.SSO,
            ),
            Legislation(
                sso_code="AA2001",
                title=_TITLE_AA,
                is_in_newest_listing=False,
                listing_source=SourceName.INTERNET_ARCHIVE,
            ),
        ]
    )
    session.commit()


def test_rows_come_back_in_code_order_and_the_count_is_two(
    scratch_session: Session,
) -> None:
    _add_two_legislations(scratch_session)

    legislation_rows = CRUDLegislation(scratch_session).get_rows()

    assert CRUDLegislation(scratch_session).get_count() == _LEGISLATION_COUNT
    assert legislation_rows == [
        LegislationRow(
            id=2,
            sso_code="AA2001",
            title=_TITLE_AA,
            is_in_newest_listing=False,
            listing_source=SourceName.INTERNET_ARCHIVE,
        ),
        LegislationRow(
            id=1,
            sso_code="TCA2005",
            title=_TITLE_TCA,
            is_in_newest_listing=True,
            listing_source=SourceName.SSO,
        ),
    ]


def test_an_update_changes_only_the_row_it_names(scratch_session: Session) -> None:
    _add_two_legislations(scratch_session)

    CRUDLegislation(scratch_session).update_many(
        [
            LegislationUpdate(
                id=2,
                title="Arbitration Act 2001 (renamed)",
                is_in_newest_listing=True,
                listing_source=SourceName.SSO,
            )
        ]
    )
    legislation_rows = CRUDLegislation(scratch_session).get_rows()

    assert legislation_rows[0].title == "Arbitration Act 2001 (renamed)"
    assert legislation_rows[0].is_in_newest_listing
    assert legislation_rows[0].listing_source == SourceName.SSO
    assert legislation_rows[1].title == _TITLE_TCA
    assert CRUDLegislation(scratch_session).get_count() == _LEGISLATION_COUNT


def test_an_empty_update_writes_nothing(scratch_session: Session) -> None:
    _add_two_legislations(scratch_session)

    CRUDLegislation(scratch_session).update_many([])

    assert CRUDLegislation(scratch_session).get_count() == _LEGISLATION_COUNT
