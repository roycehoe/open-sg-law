from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel

from crud.source_grant import CRUDSourceGrant
from enums import SourceName
from services.source_grants import (
    SITE_ROLE_NAME,
    TABLE_NAME_TO_SOURCES,
    get_table_names_to_grant,
)
from tests.site_role_seed import (
    has_site_role_select,
    load_site_role_migration,
)

_SELECT_PRIVILEGE = "SELECT"


def test_every_table_is_granted_while_every_source_but_elitigation_is_published() -> (
    None
):
    published_sources = frozenset(
        source_name
        for source_name in SourceName
        if source_name != SourceName.ELITIGATION
    )

    assert get_table_names_to_grant(published_sources) == sorted(TABLE_NAME_TO_SOURCES)


def test_withdrawing_sso_leaves_source_bill_and_bill_report() -> None:
    published_sources = frozenset(
        source_name
        for source_name in SourceName
        if source_name != SourceName.ELITIGATION and source_name != SourceName.SSO
    )

    assert get_table_names_to_grant(published_sources) == [
        "bill",
        "bill_report",
        "source",
    ]


def test_the_grant_map_names_tables_and_never_the_raw_or_run_table() -> None:
    assert set(TABLE_NAME_TO_SOURCES).issubset(SQLModel.metadata.tables)
    assert "source_response" not in TABLE_NAME_TO_SOURCES
    assert "harvest_run" not in TABLE_NAME_TO_SOURCES


def test_the_migration_map_matches_the_grant_map() -> None:
    migration = load_site_role_migration()

    assert {
        table_name: frozenset(SourceName(source_name) for source_name in source_names)
        for table_name, source_names in migration.TABLE_NAME_TO_SOURCE_NAMES
    } == TABLE_NAME_TO_SOURCES, (
        "a change to TABLE_NAME_TO_SOURCES needs a new migration that grants the same"
    )


def test_a_grant_is_read_back_and_a_revoke_removes_it(
    scratch_engine: Engine, site_role_schema: str
) -> None:
    with Session(scratch_engine) as session:
        CRUDSourceGrant(session).grant_select(
            site_role_schema, "legislation", SITE_ROLE_NAME
        )
        session.commit()

        assert CRUDSourceGrant(
            session
        ).get_table_names_by_grantee_and_privilege_type_and_table_schema(
            SITE_ROLE_NAME, _SELECT_PRIVILEGE, site_role_schema
        ) == ["legislation"]
        assert has_site_role_select(scratch_engine, site_role_schema, "legislation")

        CRUDSourceGrant(session).revoke_select(
            site_role_schema, "legislation", SITE_ROLE_NAME
        )
        session.commit()

        assert (
            CRUDSourceGrant(
                session
            ).get_table_names_by_grantee_and_privilege_type_and_table_schema(
                SITE_ROLE_NAME, _SELECT_PRIVILEGE, site_role_schema
            )
            == []
        )
    assert not has_site_role_select(scratch_engine, site_role_schema, "legislation")


def test_a_grant_rolled_back_is_never_held(
    scratch_engine: Engine, site_role_schema: str
) -> None:
    with Session(scratch_engine) as session:
        CRUDSourceGrant(session).grant_select(
            site_role_schema, "legislation", SITE_ROLE_NAME
        )
        session.rollback()

    assert not has_site_role_select(scratch_engine, site_role_schema, "legislation")
