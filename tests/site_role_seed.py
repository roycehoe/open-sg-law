import importlib.util
from pathlib import Path
from types import ModuleType

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlmodel import Session

from crud.source_grant import CRUDSourceGrant
from services.source_grants import SITE_ROLE_NAME

_MIGRATION_PATH = (
    Path(__file__).parent.parent / "alembic" / "versions" / "0012_add_site_role.py"
)
_MIGRATION_MODULE_NAME = "migration_0012_add_site_role"
_GRANT_MAP_MIGRATION_PATH = (
    Path(__file__).parent.parent
    / "alembic"
    / "versions"
    / "0013_add_judgment_tables.py"
)
_GRANT_MAP_MIGRATION_MODULE_NAME = "migration_0013_add_judgment_tables"
_SELECT_PRIVILEGE = "SELECT"


def _load_migration(module_name: str, migration_path: Path) -> ModuleType:
    module_spec = importlib.util.spec_from_file_location(module_name, migration_path)
    assert module_spec is not None
    assert module_spec.loader is not None
    migration = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(migration)
    return migration


def load_site_role_migration() -> ModuleType:
    return _load_migration(_MIGRATION_MODULE_NAME, _MIGRATION_PATH)


def load_grant_map_migration() -> ModuleType:
    return _load_migration(_GRANT_MAP_MIGRATION_MODULE_NAME, _GRANT_MAP_MIGRATION_PATH)


def create_site_role(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text(load_site_role_migration().CREATE_SITE_ROLE_STATEMENT))


def get_test_schema(engine: Engine) -> str:
    with engine.connect() as connection:
        return connection.execute(text("SELECT current_schema()")).scalar_one()


def revoke_site_role_grants(engine: Engine, schema: str) -> None:
    with Session(engine) as session:
        for table_name in CRUDSourceGrant(
            session
        ).get_table_names_by_grantee_and_privilege_type_and_table_schema(
            SITE_ROLE_NAME, _SELECT_PRIVILEGE, schema
        ):
            CRUDSourceGrant(session).revoke_select(schema, table_name, SITE_ROLE_NAME)
        session.commit()


def has_site_role_select(engine: Engine, schema: str, table_name: str) -> bool:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT has_table_privilege(:role_name, :table, :privilege_type)"),
            {
                "role_name": SITE_ROLE_NAME,
                "table": f'"{schema}"."{table_name}"',
                "privilege_type": _SELECT_PRIVILEGE,
            },
        ).scalar_one()
