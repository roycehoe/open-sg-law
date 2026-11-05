from datetime import datetime, timezone

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from crud.source import CRUDSource
from database.source import Source
from enums import SourceName, SsoAccessState
from tests.source_seed import seed_sources

_SERVING_REASON = "The listing page answered 200"


def test_get_by_name_returns_the_sso_row_untested(scratch_session: Session) -> None:
    seed_sources(scratch_session)

    source = CRUDSource(scratch_session).get_by_name(SourceName.SSO)

    assert source is not None
    assert source.name == SourceName.SSO
    assert source.sso_access_state == SsoAccessState.UNTESTED


def test_get_all_returns_the_six_rows(scratch_session: Session) -> None:
    seed_sources(scratch_session)

    sources = CRUDSource(scratch_session).get_all()

    assert [source.name for source in sources] == list(SourceName)


def test_get_all_for_update_locks_every_row(
    scratch_engine: Engine, scratch_session: Session
) -> None:
    seed_sources(scratch_session)

    sources = CRUDSource(scratch_session).get_all_for_update()

    assert [source.name for source in sources] == list(SourceName)
    with Session(scratch_engine) as session:
        with pytest.raises(OperationalError, match="could not obtain lock"):
            session.exec(
                select(Source)
                .where(Source.name == SourceName.ELITIGATION)
                .with_for_update(nowait=True)
            ).all()


def test_an_updated_state_is_visible_after_commit_in_a_new_session(
    scratch_engine: Engine, scratch_session: Session
) -> None:
    seed_sources(scratch_session)
    source = CRUDSource(scratch_session).get_by_name_for_update(SourceName.SSO)
    assert source is not None
    source.sso_access_state = SsoAccessState.SERVING
    source.sso_access_state_reason = _SERVING_REASON
    source.sso_access_state_changed_at = datetime.now(timezone.utc)

    CRUDSource(scratch_session).update(source)
    scratch_session.commit()

    with Session(scratch_engine) as session:
        stored_source = CRUDSource(session).get_by_name(SourceName.SSO)
        assert stored_source is not None
        assert stored_source.sso_access_state == SsoAccessState.SERVING
        assert stored_source.sso_access_state_reason == _SERVING_REASON
