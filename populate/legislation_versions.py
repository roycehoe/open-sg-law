from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlmodel import Session

from crud.legislation import CRUDLegislation
from crud.legislation_version import CRUDLegislationVersion
from crud.source_response import CRUDSourceResponse, DocumentRow
from database.legislation_version import LegislationVersion
from enums import ResponseKind, SourceName
from exceptions import (
    OpenSgLawCdxAnswerError,
    OpenSgLawPdfTextError,
    OpenSgLawVersionDateError,
)
from services.archive_capture import get_cdx_captures
from services.legislation_version import (
    get_newest_version_updates,
    get_printed_version_date,
)
from utils.archive_capture_url import (
    ArchiveCapture,
    get_archive_capture,
    get_capture_time,
)
from utils.pdf_text import get_pdf_pages
from utils.sso_act_url import SsoActPdf, get_sso_act_pdf

_HTTP_OK = 200
_NOT_A_PLAIN_ACT_PDF_REASON = "not a plain Act PDF"
_NOT_AN_ARCHIVE_CAPTURE_REASON = "not an archive capture URL"


@dataclass(frozen=True)
class SkippedDocument:
    requested_url: str
    reason: str


@dataclass(frozen=True)
class LegislationVersionWrite:
    legislation_versions_to_insert: list[LegislationVersion]
    skipped_documents: list[SkippedDocument]
    skipped_cdx_answer_count: int


@dataclass(frozen=True)
class CaptureDigests:
    capture_to_digest: dict[tuple[str, str], str]
    skipped_cdx_answer_count: int


def _get_capture_digests(session: Session) -> CaptureDigests:
    capture_to_digest: dict[tuple[str, str], str] = {}
    skipped_cdx_answer_count = 0
    for cdx_answer_text in CRUDSourceResponse(
        session
    ).get_body_texts_by_source_and_kind_and_status_code_and_body_text_not_null(
        SourceName.INTERNET_ARCHIVE, ResponseKind.CDX_ANSWER, _HTTP_OK
    ):
        try:
            cdx_captures = get_cdx_captures(cdx_answer_text)
        except OpenSgLawCdxAnswerError:
            skipped_cdx_answer_count += 1
            continue
        for cdx_capture in cdx_captures:
            capture_to_digest[(cdx_capture.timestamp, cdx_capture.original_url)] = (
                cdx_capture.digest
            )
    return CaptureDigests(
        capture_to_digest=capture_to_digest,
        skipped_cdx_answer_count=skipped_cdx_answer_count,
    )


def _get_captured_at(
    document_row: DocumentRow, archive_capture: Optional[ArchiveCapture]
) -> datetime:
    if archive_capture is None:
        return document_row.fetched_at
    return get_capture_time(archive_capture.timestamp)


def _build_legislation_version(
    session: Session,
    document_row: DocumentRow,
    sso_act_pdf: SsoActPdf,
    legislation_id: int,
    archive_capture: Optional[ArchiveCapture],
    capture_to_digest: dict[tuple[str, str], str],
) -> LegislationVersion:
    pdf_pages = get_pdf_pages(
        CRUDSourceResponse(session).get_body_bytes_by_id_and_body_bytes_not_null(
            document_row.id
        )
    )
    printed_version_date = get_printed_version_date(pdf_pages)
    return LegislationVersion(
        printed_version_date=(
            None if printed_version_date is None else printed_version_date.printed_text
        ),
        version_date=(
            None if printed_version_date is None else printed_version_date.version_date
        ),
        version_stamp=sso_act_pdf.version_stamp,
        archive_timestamp=(
            None if archive_capture is None else archive_capture.timestamp
        ),
        archive_digest=(
            None
            if archive_capture is None
            else capture_to_digest.get(
                (archive_capture.timestamp, archive_capture.original_url)
            )
        ),
        captured_at=_get_captured_at(document_row, archive_capture),
        is_newest=False,
        source=document_row.source,
        legislation_id=legislation_id,
        source_response_id=document_row.id,
    )


def get_legislation_version_write(session: Session) -> LegislationVersionWrite:
    document_rows = CRUDSourceResponse(
        session
    ).get_document_rows_by_kind_and_status_code_and_body_bytes_not_null(
        ResponseKind.DOCUMENT, _HTTP_OK
    )
    stored_source_response_ids = {
        legislation_version_row.source_response_id
        for legislation_version_row in CRUDLegislationVersion(session).get_rows()
    }
    sso_code_to_legislation_id = {
        legislation_row.sso_code: legislation_row.id
        for legislation_row in CRUDLegislation(session).get_rows()
    }
    capture_digests = _get_capture_digests(session)
    legislation_versions_to_insert: list[LegislationVersion] = []
    skipped_documents: list[SkippedDocument] = []
    for document_row in document_rows:
        if document_row.id in stored_source_response_ids:
            continue
        sso_act_pdf = get_sso_act_pdf(document_row.requested_url)
        if sso_act_pdf is None:
            skipped_documents.append(
                SkippedDocument(document_row.requested_url, _NOT_A_PLAIN_ACT_PDF_REASON)
            )
            continue
        legislation_id = sso_code_to_legislation_id.get(sso_act_pdf.sso_code)
        if legislation_id is None:
            skipped_documents.append(
                SkippedDocument(
                    document_row.requested_url,
                    f"no legislation row for {sso_act_pdf.sso_code}",
                )
            )
            continue
        archive_capture = get_archive_capture(document_row.requested_url)
        if (
            document_row.source == SourceName.INTERNET_ARCHIVE
            and archive_capture is None
        ):
            skipped_documents.append(
                SkippedDocument(
                    document_row.requested_url, _NOT_AN_ARCHIVE_CAPTURE_REASON
                )
            )
            continue
        try:
            legislation_versions_to_insert.append(
                _build_legislation_version(
                    session,
                    document_row,
                    sso_act_pdf,
                    legislation_id,
                    archive_capture,
                    capture_digests.capture_to_digest,
                )
            )
        except OpenSgLawPdfTextError as error:
            skipped_documents.append(
                SkippedDocument(document_row.requested_url, str(error))
            )
        except OpenSgLawVersionDateError as error:
            skipped_documents.append(
                SkippedDocument(document_row.requested_url, str(error))
            )
    return LegislationVersionWrite(
        legislation_versions_to_insert=legislation_versions_to_insert,
        skipped_documents=skipped_documents,
        skipped_cdx_answer_count=capture_digests.skipped_cdx_answer_count,
    )


def write_legislation_versions(
    session: Session, legislation_version_write: LegislationVersionWrite
) -> int:
    CRUDLegislationVersion(session).add_many(
        legislation_version_write.legislation_versions_to_insert
    )
    return CRUDLegislationVersion(session).set_is_newest_bulk(
        get_newest_version_updates(CRUDLegislationVersion(session).get_rows())
    )
