from datetime import datetime, timezone

from utils.archive_capture_url import (
    ArchiveCapture,
    get_archive_capture,
    get_capture_time,
)

_IA1965_ORIGINAL_URL = "https://sso.agc.gov.sg/Act/IA1965?ViewType=Pdf&_=20251216194555"
_IA1965_ARCHIVE_URL = (
    f"https://web.archive.org/web/20260101041857id_/{_IA1965_ORIGINAL_URL}"
)


def test_an_archive_url_gives_its_timestamp_and_original_url() -> None:
    assert get_archive_capture(_IA1965_ARCHIVE_URL) == ArchiveCapture(
        timestamp="20260101041857", original_url=_IA1965_ORIGINAL_URL
    )


def test_an_sso_url_is_not_an_archive_capture() -> None:
    assert get_archive_capture(_IA1965_ORIGINAL_URL) is None


def test_a_timestamp_gives_its_utc_time() -> None:
    assert get_capture_time("20260101041857") == datetime(
        2026, 1, 1, 4, 18, 57, tzinfo=timezone.utc
    )
