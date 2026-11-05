from sqlalchemy import text
from sqlmodel import Session


class CRUDSourceGrant:
    def __init__(self, session: Session):
        self.session = session

    def get_table_names_by_grantee_and_privilege_type_and_table_schema(
        self, grantee: str, privilege_type: str, table_schema: str
    ) -> list[str]:
        statement = text(
            "SELECT table_name FROM information_schema.role_table_grants"
            " WHERE grantee = :grantee"
            " AND privilege_type = :privilege_type"
            " AND table_schema = :table_schema"
            " ORDER BY table_name"
        )
        return list(
            self.session.execute(
                statement,
                {
                    "grantee": grantee,
                    "privilege_type": privilege_type,
                    "table_schema": table_schema,
                },
            )
            .scalars()
            .all()
        )

    def grant_select(self, table_schema: str, table_name: str, role_name: str) -> None:
        identifier_preparer = self.session.get_bind().dialect.identifier_preparer
        statement = text(
            f"GRANT SELECT ON TABLE {identifier_preparer.quote(table_schema)}.{identifier_preparer.quote(table_name)}"
            f" TO {identifier_preparer.quote(role_name)}"
        )
        self.session.execute(statement)

    def revoke_select(self, table_schema: str, table_name: str, role_name: str) -> None:
        identifier_preparer = self.session.get_bind().dialect.identifier_preparer
        statement = text(
            f"REVOKE SELECT ON TABLE {identifier_preparer.quote(table_schema)}.{identifier_preparer.quote(table_name)}"
            f" FROM {identifier_preparer.quote(role_name)}"
        )
        self.session.execute(statement)
