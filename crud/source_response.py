from dataclasses import dataclass
from datetime import datetime
from typing import Optional, cast

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session, col, func, select

from database.source_response import SourceResponse
from enums import ResponseKind, SourceName


@dataclass(frozen=True)
class ListingPageRow:
    id: int
    requested_url: str
    final_url: str
    content_type: Optional[str]
    body_text: Optional[str]
    fetched_at: datetime
    source: SourceName
    harvest_run_id: int


@dataclass(frozen=True)
class DocumentRow:
    id: int
    requested_url: str
    fetched_at: datetime
    source: SourceName


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

    def get_requested_urls_by_source_and_kind_and_status_code_and_body_bytes_not_null(
        self, source: SourceName, kind: ResponseKind, status_code: int
    ) -> list[str]:
        statement = (
            select(SourceResponse.requested_url)
            .where(SourceResponse.source == source)
            .where(SourceResponse.kind == kind)
            .where(SourceResponse.status_code == status_code)
            .where(col(SourceResponse.body_bytes).is_not(None))
        )
        return list(self.session.exec(statement).all())

    def get_count_by_source_and_kind_and_status_code(
        self, source: SourceName, kind: ResponseKind, status_code: int
    ) -> int:
        statement = (
            select(func.count())
            .select_from(SourceResponse)
            .where(SourceResponse.source == source)
            .where(SourceResponse.kind == kind)
            .where(SourceResponse.status_code == status_code)
        )
        return self.session.exec(statement).one()

    def get_listing_page_rows_by_kind_and_status_code(
        self, kind: ResponseKind, status_code: int
    ) -> list[ListingPageRow]:
        statement = (
            select(  # pyright: ignore[reportCallIssue] sqlmodel types select for at most four columns
                SourceResponse.id,
                SourceResponse.requested_url,
                SourceResponse.final_url,
                SourceResponse.content_type,
                SourceResponse.body_text,
                SourceResponse.fetched_at,
                SourceResponse.source,
                SourceResponse.harvest_run_id,
            )
            .where(SourceResponse.kind == kind)
            .where(SourceResponse.status_code == status_code)
            .order_by(SourceResponse.harvest_run_id, col(SourceResponse.id))
        )
        return [ListingPageRow(*row) for row in self.session.exec(statement).all()]

    def get_document_rows_by_kind_and_status_code_and_body_bytes_not_null(
        self, kind: ResponseKind, status_code: int
    ) -> list[DocumentRow]:
        statement = (
            select(
                SourceResponse.id,
                SourceResponse.requested_url,
                SourceResponse.fetched_at,
                SourceResponse.source,
            )
            .where(SourceResponse.kind == kind)
            .where(SourceResponse.status_code == status_code)
            .where(col(SourceResponse.body_bytes).is_not(None))
            .order_by(col(SourceResponse.id))
        )
        return [DocumentRow(*row) for row in self.session.exec(statement).all()]

    def get_body_bytes_by_id(self, source_response_id: int) -> bytes:
        statement = (
            select(SourceResponse.body_bytes)
            .where(col(SourceResponse.id) == source_response_id)
            .where(col(SourceResponse.body_bytes).is_not(None))
        )
        return cast(bytes, self.session.exec(statement).one())

    def get_body_texts_by_source_and_kind_and_status_code(
        self, source: SourceName, kind: ResponseKind, status_code: int
    ) -> list[str]:
        statement = (
            select(SourceResponse.body_text)
            .where(SourceResponse.source == source)
            .where(SourceResponse.kind == kind)
            .where(SourceResponse.status_code == status_code)
            .where(col(SourceResponse.body_text).is_not(None))
            .order_by(col(SourceResponse.id))
        )
        return [
            cast(str, body_text) for body_text in self.session.exec(statement).all()
        ]
