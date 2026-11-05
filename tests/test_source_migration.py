import importlib.util
from collections import Counter
from pathlib import Path
from typing import Optional

from enums import PublishStatus, SourceName, SsoAccessState

_MIGRATION_PATH = (
    Path(__file__).parent.parent / "alembic" / "versions" / "0002_add_source.py"
)
_MIGRATION_MODULE_NAME = "migration_0002_add_source"


def _get_source_rows() -> tuple[dict[str, Optional[str]], ...]:
    spec = importlib.util.spec_from_file_location(
        _MIGRATION_MODULE_NAME, _MIGRATION_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration.SOURCE_ROWS


def test_the_source_rows_name_every_source_once() -> None:
    source_rows = _get_source_rows()

    assert Counter(source_row["name"] for source_row in source_rows) == Counter(
        source_name.value for source_name in SourceName
    )


def test_only_elitigation_is_unpublished() -> None:
    source_rows = _get_source_rows()

    assert [
        source_row["name"]
        for source_row in source_rows
        if source_row["publish_status"] != PublishStatus.PUBLISHED
    ] == [SourceName.ELITIGATION]
    assert [
        source_row["publish_status"]
        for source_row in source_rows
        if source_row["name"] == SourceName.ELITIGATION
    ] == [PublishStatus.UNPUBLISHED]


def test_only_sso_has_an_access_state_and_it_is_untested() -> None:
    source_rows = _get_source_rows()

    assert {
        source_row["name"]: source_row["sso_access_state"]
        for source_row in source_rows
        if source_row["sso_access_state"] is not None
    } == {SourceName.SSO: SsoAccessState.UNTESTED}
