from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col

from database.source_response import SourceResponse


class CRUDSourceResponse:
    def __init__(self, session: Session):
        self.session = session

    def insert_on_conflict_do_nothing(self, source_response: SourceResponse) -> bool:
        statement = (
            insert(SourceResponse)
            .values(
                requested_url=source_response.requested_url,
                final_url=source_response.final_url,
                status_code=source_response.status_code,
                content_type=source_response.content_type,
                body_text=source_response.body_text,
                body_bytes=source_response.body_bytes,
                sha256=source_response.sha256,
                byte_length=source_response.byte_length,
                fetched_at=source_response.fetched_at,
                kind=source_response.kind,
                source=source_response.source,
                harvest_run_id=source_response.harvest_run_id,
            )
            .on_conflict_do_nothing(
                constraint="uq_source_response_requested_url_sha256"
            )
            .returning(col(SourceResponse.id))
        )
        return self.session.execute(statement).first() is not None
