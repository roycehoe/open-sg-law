from sqlalchemy import text
from sqlmodel import Session


class CRUDDatabaseSize:
    def __init__(self, session: Session):
        self.session = session

    def get_current_database_bytes(self) -> int:
        statement = text("SELECT pg_database_size(current_database())")
        return self.session.execute(statement).scalar_one()
