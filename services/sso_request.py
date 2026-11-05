from datetime import datetime, time
from typing import Optional
from zoneinfo import ZoneInfo

from enums import SsoAccessState
from exceptions import OpenSgLawSourceStateError, OpenSgLawSsoWindowError
from utils.sso_act_url import get_sso_act_pdf
from utils.sso_listing import SsoListingRow

_SINGAPORE = ZoneInfo("Asia/Singapore")
_WINDOW_START = time(3, 0)
_WINDOW_CUTOFF = time(6, 55)


def validate_can_send_sso_request(
    now: datetime, sso_access_state: Optional[SsoAccessState]
) -> None:
    if sso_access_state == SsoAccessState.CHALLENGED:
        raise OpenSgLawSourceStateError(
            "SSO is CHALLENGED; nothing is sent until clear_sso_challenge runs after AGC replies"
        )
    singapore_time = now.astimezone(_SINGAPORE).time()
    if singapore_time < _WINDOW_START:
        raise OpenSgLawSsoWindowError(
            f"{singapore_time:%H:%M} SGT is before the 03:00 window"
        )
    if singapore_time >= _WINDOW_CUTOFF:
        raise OpenSgLawSsoWindowError(
            f"{singapore_time:%H:%M} SGT is past the 06:55 cutoff"
        )


def get_act_pdf_paths_to_fetch(
    listing_rows: list[SsoListingRow], stored_document_urls: list[str]
) -> list[str]:
    sso_code_to_stored_stamps: dict[str, set[str]] = {}
    for stored_document_url in stored_document_urls:
        sso_act_pdf = get_sso_act_pdf(stored_document_url)
        if sso_act_pdf is None:
            continue
        if sso_act_pdf.version_stamp is None:
            continue
        sso_code_to_stored_stamps.setdefault(sso_act_pdf.sso_code, set()).add(
            sso_act_pdf.version_stamp
        )
    rows_to_fetch = [
        listing_row
        for listing_row in listing_rows
        if listing_row.version_stamp
        not in sso_code_to_stored_stamps.get(listing_row.sso_code, set())
    ]
    return [
        listing_row.pdf_path
        for listing_row in sorted(
            rows_to_fetch,
            key=lambda listing_row: (
                max(sso_code_to_stored_stamps.get(listing_row.sso_code, {""})),
                listing_row.sso_code,
            ),
        )
    ]
