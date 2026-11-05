import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from settings import settings

CAPTURE_TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"
_CAPTURE_PATH = "/web/{timestamp}id_/{original_url}"
_CAPTURE_URL_PATTERN = re.compile(r"/web/(\d{14})id_/(.+)$")


@dataclass(frozen=True)
class ArchiveCapture:
    timestamp: str
    original_url: str


def build_archive_capture_url(timestamp: str, original_url: str) -> str:
    capture_path = _CAPTURE_PATH.format(timestamp=timestamp, original_url=original_url)
    return f"{settings.internet_archive_base_url}{capture_path}"


def get_archive_capture(url: str) -> Optional[ArchiveCapture]:
    match = _CAPTURE_URL_PATTERN.search(url)
    if match is None:
        return None
    return ArchiveCapture(timestamp=match.group(1), original_url=match.group(2))


def get_capture_time(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, CAPTURE_TIMESTAMP_FORMAT).replace(
        tzinfo=timezone.utc
    )
