from datetime import date, datetime, timezone

from sqlmodel import Session, select

from crud.legislation_version import CRUDLegislationVersion
from database.legislation_version import LegislationVersion
from enums import SourceName
from populate.legislation_versions import (
    SkippedDocument,
    get_legislation_version_write,
    write_legislation_versions,
)
from tests.document_seed import (
    AA1906_ARCHIVE_URL,
    AA1906_BODY,
    ARCHIVE_FETCHED_AT,
    IA1965_ARCHIVE_TIMESTAMP,
    IA1965_ARCHIVE_URL,
    IA1965_BODY,
    IA1965_ORIGINAL_URL,
    IA1965_OTHER_SSO_URL,
    IA1965_POINT_IN_TIME_URL,
    SSO_FETCHED_AT,
    build_cdx_answer_text,
    seed_cdx_answer,
    seed_document,
    seed_harvest_run,
    seed_legislation,
)
from tests.listing_seed import OFFLINE_PAGE_BODY
from tests.source_seed import seed_sources

_IA1965_TITLE = "Interpretation Act 1965"
_ARCHIVE_CAPTURED_AT = datetime(2026, 1, 1, 4, 18, 57, tzinfo=timezone.utc)
_PRINTED_VERSION_DATE = "25/11/2024"
_VERSION_DATE = date(2024, 11, 25)
_UNREADABLE_BODY = b"not a pdf"
_FLAG_COUNT = 2


def _seed_archive_copy(session: Session) -> None:
    seed_sources(session)
    seed_legislation(session, {"IA1965": _IA1965_TITLE})
    seed_document(
        session,
        seed_harvest_run(session, SourceName.INTERNET_ARCHIVE),
        SourceName.INTERNET_ARCHIVE,
        IA1965_ARCHIVE_URL,
        IA1965_BODY,
        ARCHIVE_FETCHED_AT,
    )


def _get_stored_versions(session: Session) -> list[LegislationVersion]:
    session.expire_all()
    return list(session.exec(select(LegislationVersion)).all())


def test_an_archive_copy_gets_its_date_capture_time_and_digest(
    scratch_session: Session,
) -> None:
    _seed_archive_copy(scratch_session)
    seed_cdx_answer(
        scratch_session,
        seed_harvest_run(scratch_session, SourceName.INTERNET_ARCHIVE),
        build_cdx_answer_text(IA1965_ORIGINAL_URL, IA1965_ARCHIVE_TIMESTAMP),
    )

    legislation_version_write = get_legislation_version_write(scratch_session)
    write_legislation_versions(scratch_session, legislation_version_write)

    (legislation_version,) = _get_stored_versions(scratch_session)
    assert legislation_version.legislation_id == 1
    assert legislation_version.source == SourceName.INTERNET_ARCHIVE
    assert legislation_version.printed_version_date == _PRINTED_VERSION_DATE
    assert legislation_version.version_date == _VERSION_DATE
    assert legislation_version.archive_timestamp == IA1965_ARCHIVE_TIMESTAMP
    assert legislation_version.archive_digest == ""
    assert legislation_version.captured_at == _ARCHIVE_CAPTURED_AT
    assert legislation_version.version_stamp == "20251216194555"
    assert legislation_version.is_newest is True


def test_an_archive_copy_no_stored_answer_lists_has_no_digest(
    scratch_session: Session,
) -> None:
    _seed_archive_copy(scratch_session)

    write_legislation_versions(
        scratch_session, get_legislation_version_write(scratch_session)
    )

    (legislation_version,) = _get_stored_versions(scratch_session)
    assert legislation_version.archive_digest is None


def test_a_later_sso_copy_with_the_same_printed_date_becomes_newest(
    scratch_session: Session,
) -> None:
    _seed_archive_copy(scratch_session)
    write_legislation_versions(
        scratch_session, get_legislation_version_write(scratch_session)
    )
    seed_document(
        scratch_session,
        seed_harvest_run(scratch_session, SourceName.SSO),
        SourceName.SSO,
        IA1965_ORIGINAL_URL,
        IA1965_BODY,
        SSO_FETCHED_AT,
    )

    flag_count = write_legislation_versions(
        scratch_session, get_legislation_version_write(scratch_session)
    )

    assert flag_count == _FLAG_COUNT
    source_to_is_newest = {
        legislation_version.source: legislation_version.is_newest
        for legislation_version in _get_stored_versions(scratch_session)
    }
    assert source_to_is_newest == {
        SourceName.INTERNET_ARCHIVE: False,
        SourceName.SSO: True,
    }
    sso_version = next(
        legislation_version
        for legislation_version in _get_stored_versions(scratch_session)
        if legislation_version.source == SourceName.SSO
    )
    assert sso_version.captured_at == SSO_FETCHED_AT
    assert sso_version.archive_timestamp is None


def test_a_document_that_is_not_a_pdf_is_skipped_with_the_pdf_text_message(
    scratch_session: Session,
) -> None:
    seed_sources(scratch_session)
    seed_legislation(scratch_session, {"IA1965": _IA1965_TITLE})
    seed_document(
        scratch_session,
        seed_harvest_run(scratch_session, SourceName.SSO),
        SourceName.SSO,
        IA1965_OTHER_SSO_URL,
        _UNREADABLE_BODY,
        SSO_FETCHED_AT,
    )

    legislation_version_write = get_legislation_version_write(scratch_session)

    assert legislation_version_write.legislation_versions_to_insert == []
    assert legislation_version_write.skipped_documents == [
        SkippedDocument(IA1965_OTHER_SSO_URL, "The body is not a readable PDF")
    ]


def test_a_url_for_an_unknown_code_is_skipped(scratch_session: Session) -> None:
    seed_sources(scratch_session)
    seed_legislation(scratch_session, {"IA1965": _IA1965_TITLE})
    seed_document(
        scratch_session,
        seed_harvest_run(scratch_session, SourceName.INTERNET_ARCHIVE),
        SourceName.INTERNET_ARCHIVE,
        AA1906_ARCHIVE_URL,
        AA1906_BODY,
        ARCHIVE_FETCHED_AT,
    )

    legislation_version_write = get_legislation_version_write(scratch_session)

    assert legislation_version_write.legislation_versions_to_insert == []
    assert legislation_version_write.skipped_documents == [
        SkippedDocument(AA1906_ARCHIVE_URL, "no legislation row for AA1906")
    ]


def test_a_point_in_time_url_is_skipped_as_not_a_plain_act_pdf(
    scratch_session: Session,
) -> None:
    seed_sources(scratch_session)
    seed_legislation(scratch_session, {"IA1965": _IA1965_TITLE})
    seed_document(
        scratch_session,
        seed_harvest_run(scratch_session, SourceName.SSO),
        SourceName.SSO,
        IA1965_POINT_IN_TIME_URL,
        IA1965_BODY,
        SSO_FETCHED_AT,
    )

    legislation_version_write = get_legislation_version_write(scratch_session)

    assert legislation_version_write.skipped_documents == [
        SkippedDocument(IA1965_POINT_IN_TIME_URL, "not a plain Act PDF")
    ]


def test_the_offline_page_is_a_skipped_cdx_answer_and_gives_no_digest(
    scratch_session: Session,
) -> None:
    _seed_archive_copy(scratch_session)
    seed_cdx_answer(
        scratch_session,
        seed_harvest_run(scratch_session, SourceName.INTERNET_ARCHIVE),
        OFFLINE_PAGE_BODY.decode("utf-8"),
    )

    legislation_version_write = get_legislation_version_write(scratch_session)

    assert legislation_version_write.skipped_cdx_answer_count == 1
    assert len(legislation_version_write.legislation_versions_to_insert) == 1


def test_a_second_plan_after_the_write_inserts_nothing(
    scratch_session: Session,
) -> None:
    _seed_archive_copy(scratch_session)
    write_legislation_versions(
        scratch_session, get_legislation_version_write(scratch_session)
    )

    legislation_version_write = get_legislation_version_write(scratch_session)

    assert legislation_version_write.legislation_versions_to_insert == []
    assert legislation_version_write.skipped_documents == []
    assert CRUDLegislationVersion(scratch_session).get_count() == 1
