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

    def has_privilege_by_grantee_and_table_name_and_privilege_type(
        self, grantee: str, table_name: str, privilege_type: str
    ) -> bool:
        statement = text(
            "SELECT has_table_privilege(:grantee, :table_name, :privilege_type)"
        )
        return self.session.execute(
            statement,
            {
                "grantee": grantee,
                "table_name": table_name,
                "privilege_type": privilege_type,
            },
        ).scalar_one()

    def _get_quoted_identifier(self, identifier: str) -> str:
        return self.session.get_bind().dialect.identifier_preparer.quote(identifier)

    def grant_select(self, table_schema: str, table_name: str, role_name: str) -> None:
        statement = text(
            f"GRANT SELECT ON TABLE {self._get_quoted_identifier(table_schema)}.{self._get_quoted_identifier(table_name)}"
            f" TO {self._get_quoted_identifier(role_name)}"
        )
        self.session.execute(statement)

    def revoke_select(self, table_schema: str, table_name: str, role_name: str) -> None:
        statement = text(
            f"REVOKE SELECT ON TABLE {self._get_quoted_identifier(table_schema)}.{self._get_quoted_identifier(table_name)}"
            f" FROM {self._get_quoted_identifier(role_name)}"
        )
        self.session.execute(statement)
