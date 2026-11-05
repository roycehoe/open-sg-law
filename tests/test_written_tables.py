import pytest
from sqlmodel import Session

from crud.vacuum import CRUDVacuum
from database.source import Source
from exceptions import OpenSgLawWriteCheckError
from populate.written_tables import vacuum_analyze_written_tables
from tests.source_seed import seed_sources


def _skip_vacuum_analyze(*args: object) -> None:
    pass


def test_vacuum_runs_on_every_written_table(scratch_session: Session) -> None:
    seed_sources(scratch_session)
    table_names: list[str] = [Source.__tablename__]  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr
    vacuum_counts_before = [
        CRUDVacuum(scratch_session).get_vacuum_count(table_name)
        for table_name in table_names
    ]
    scratch_session.commit()

    vacuum_analyze_written_tables(scratch_session, table_names)

    assert [
        CRUDVacuum(scratch_session).get_vacuum_count(table_name)
        for table_name in table_names
    ] == [vacuum_count + 1 for vacuum_count in vacuum_counts_before]


def test_skipped_vacuum_fails_loudly(
    scratch_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed_sources(scratch_session)
    monkeypatch.setattr(CRUDVacuum, "vacuum_analyze", _skip_vacuum_analyze)

    with pytest.raises(
        OpenSgLawWriteCheckError, match=r"VACUUM \(ANALYZE\) did not run on source"
    ):
        vacuum_analyze_written_tables(
            scratch_session,
            [Source.__tablename__],  # pyright: ignore[reportArgumentType] sqlmodel types __tablename__ as a declared_attr
        )
