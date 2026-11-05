"""add site role

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-05 21:30:00.000000

"""

from typing import Optional, Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: Optional[Union[str, Sequence[str]]] = "0011"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None

_SITE_ROLE_NAME = "open_sg_law_site"
_PUBLIC_SCHEMA = "public"
_PUBLISHED = "PUBLISHED"
CREATE_SITE_ROLE_STATEMENT = (
    "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'open_sg_law_site') "
    "THEN CREATE ROLE open_sg_law_site NOLOGIN; END IF; END $$;"
)
TABLE_NAME_TO_SOURCE_NAMES = (
    ("source", ()),
    ("legislation", ("SSO", "INTERNET_ARCHIVE")),
    ("legislation_version", ("SSO", "INTERNET_ARCHIVE")),
    ("legislation_section", ("SSO", "INTERNET_ARCHIVE")),
    ("legislation_alias", ("SSO", "INTERNET_ARCHIVE")),
    ("bill", ("OPENHANSARD_LINKS",)),
    ("bill_report", ("OPENHANSARD_LINKS",)),
    ("act_history_entry", ("OPENHANSARD_LINKS", "SSO")),
)


def upgrade() -> None:
    connection = op.get_bind()
    identifier_preparer = connection.dialect.identifier_preparer
    quoted_role_name = identifier_preparer.quote(_SITE_ROLE_NAME)
    quoted_schema = identifier_preparer.quote(_PUBLIC_SCHEMA)
    op.execute(CREATE_SITE_ROLE_STATEMENT)
    op.execute(f"GRANT USAGE ON SCHEMA {quoted_schema} TO {quoted_role_name}")
    published_source_names = frozenset(
        connection.execute(
            sa.text("SELECT name FROM source WHERE publish_status = :publish_status"),
            {"publish_status": _PUBLISHED},
        ).scalars()
    )
    for table_name, source_names in TABLE_NAME_TO_SOURCE_NAMES:
        if published_source_names.issuperset(source_names):
            op.execute(
                f"GRANT SELECT ON TABLE {quoted_schema}.{identifier_preparer.quote(table_name)} TO {quoted_role_name}"
            )


def downgrade() -> None:
    identifier_preparer = op.get_bind().dialect.identifier_preparer
    quoted_role_name = identifier_preparer.quote(_SITE_ROLE_NAME)
    quoted_schema = identifier_preparer.quote(_PUBLIC_SCHEMA)
    for table_name, _source_names in TABLE_NAME_TO_SOURCE_NAMES:
        op.execute(
            f"REVOKE SELECT ON TABLE {quoted_schema}.{identifier_preparer.quote(table_name)} FROM {quoted_role_name}"
        )
    op.execute(f"REVOKE USAGE ON SCHEMA {quoted_schema} FROM {quoted_role_name}")
