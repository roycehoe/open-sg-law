from datetime import datetime
from zoneinfo import ZoneInfo

from services.sso_request import get_sso_window_status, get_sso_window_text

_SINGAPORE = ZoneInfo("Asia/Singapore")


def test_the_window_text_names_the_start_and_the_cutoff() -> None:
    assert get_sso_window_text() == "03:00 to 06:55 SGT"


def test_the_window_status_gives_the_singapore_time_and_the_window() -> None:
    now = datetime(2026, 11, 6, 4, 30, tzinfo=_SINGAPORE)

    assert (
        get_sso_window_status(now)
        == "It is 04:30 SGT; requests go only from 03:00 to 06:55 SGT"
    )
