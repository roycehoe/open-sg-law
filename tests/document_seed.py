import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from crud.harvest_run import CRUDHarvestRun
from crud.legislation import CRUDLegislation
from crud.legislation_version import CRUDLegislationVersion
from crud.source_response import CRUDSourceResponse
from database.harvest_run import HarvestRun
from database.legislation import Legislation
from database.legislation_version import LegislationVersion
from database.source_response import SourceResponse
from enums import ResponseKind, SourceName
from tests.legislation_version_seed import build_version
from tests.source_seed import seed_sources

_FIXTURES_DIRECTORY = Path(__file__).parent / "fixtures"
IA1965_BODY = (_FIXTURES_DIRECTORY / "pdf" / "IA1965-p5-6.pdf").read_bytes()
AA1906_BODY = (_FIXTURES_DIRECTORY / "pdf" / "AA1906-p3-4.pdf").read_bytes()
IA1965_ORIGINAL_URL = "https://sso.agc.gov.sg/Act/IA1965?ViewType=Pdf&_=20251216194555"
IA1965_ARCHIVE_TIMESTAMP = "20260101041857"
IA1965_ARCHIVE_URL = (
    f"https://web.archive.org/web/{IA1965_ARCHIVE_TIMESTAMP}id_/{IA1965_ORIGINAL_URL}"
)
IA1965_OTHER_SSO_URL = "https://sso.agc.gov.sg/Act/IA1965?ViewType=Pdf&_=20241128233839"
IA1965_POINT_IN_TIME_URL = "https://sso.agc.gov.sg/Act/IA1965?TransactionDate=20240524235959&ViewType=Pdf&_=20240924025421"
AA1906_ORIGINAL_URL = "https://sso.agc.gov.sg/Act/AA1906?ViewType=Pdf&_=20240203013120"
AA1906_ARCHIVE_TIMESTAMP = "20251231140314"
AA1906_ARCHIVE_URL = (
    f"https://web.archive.org/web/{AA1906_ARCHIVE_TIMESTAMP}id_/{AA1906_ORIGINAL_URL}"
)
SSO_FETCHED_AT = datetime(2026, 11, 5, 19, 0, tzinfo=timezone.utc)
ARCHIVE_FETCHED_AT = datetime(2026, 11, 5, 18, 0, tzinfo=timezone.utc)


def build_cdx_answer_text(original_url: str, timestamp: str) -> str:
    return json.dumps(
        [["original", "timestamp", "digest"], [original_url, timestamp, ""]]
    )


def seed_harvest_run(session: Session, source: SourceName) -> int:
    harvest_run = HarvestRun(source=source)
    CRUDHarvestRun(session).create(harvest_run)
    assert harvest_run.id is not None
    return harvest_run.id


def seed_legislation(session: Session, sso_codes_to_titles: dict[str, str]) -> None:
    CRUDLegislation(session).add_many(
        [
            Legislation(
                sso_code=sso_code,
                title=title,
                is_in_newest_listing=True,
                listing_source=SourceName.SSO,
            )
            for sso_code, title in sso_codes_to_titles.items()
        ]
    )
    session.commit()


def seed_document(
    session: Session,
    harvest_run_id: int,
    source: SourceName,
    requested_url: str,
    body_bytes: bytes,
    fetched_at: datetime,
) -> None:
    CRUDSourceResponse(session).insert_on_conflict_do_nothing(
        SourceResponse(
            requested_url=requested_url,
            final_url=requested_url,
            status_code=200,
            body_bytes=body_bytes,
            sha256=hashlib.sha256(body_bytes).hexdigest(),
            byte_length=len(body_bytes),
            fetched_at=fetched_at,
            kind=ResponseKind.DOCUMENT,
            source=source,
            harvest_run_id=harvest_run_id,
        )
    )
    session.commit()


def seed_cdx_answer(session: Session, harvest_run_id: int, body_text: str) -> None:
    body_bytes = body_text.encode()
    CRUDSourceResponse(session).insert_on_conflict_do_nothing(
        SourceResponse(
            requested_url="https://web.archive.org/cdx/search/cdx",
            final_url="https://web.archive.org/cdx/search/cdx",
            status_code=200,
            body_text=body_text,
            sha256=hashlib.sha256(body_bytes).hexdigest(),
            byte_length=len(body_bytes),
            fetched_at=ARCHIVE_FETCHED_AT,
            kind=ResponseKind.CDX_ANSWER,
            source=SourceName.INTERNET_ARCHIVE,
            harvest_run_id=harvest_run_id,
        )
    )
    session.commit()


def seed_ia1965_version(session: Session) -> int:
    seed_sources(session)
    seed_legislation(session, {"IA1965": "Interpretation Act 1965"})
    seed_document(
        session,
        seed_harvest_run(session, SourceName.SSO),
        SourceName.SSO,
        IA1965_ORIGINAL_URL,
        IA1965_BODY,
        SSO_FETCHED_AT,
    )
    source_response_id = session.exec(select(SourceResponse.id)).one()
    assert source_response_id is not None
    CRUDLegislationVersion(session).add_many([build_version(source_response_id)])
    session.commit()
    legislation_version_id = session.exec(select(LegislationVersion.id)).one()
    assert legislation_version_id is not None
    return legislation_version_id
