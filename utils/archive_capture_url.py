from settings import settings

_CAPTURE_PATH = "/web/{timestamp}id_/{original_url}"


def build_archive_capture_url(timestamp: str, original_url: str) -> str:
    capture_path = _CAPTURE_PATH.format(timestamp=timestamp, original_url=original_url)
    return f"{settings.internet_archive_base_url}{capture_path}"
