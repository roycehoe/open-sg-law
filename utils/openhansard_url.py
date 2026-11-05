from urllib.parse import quote

_REPORT_URL_PREFIX = "https://openhansard.sg/reports/"
_REPORT_ID_SUFFIX = "#"


def get_openhansard_report_url(sprs_report_id: str) -> str:
    return _REPORT_URL_PREFIX + quote(sprs_report_id.rstrip(_REPORT_ID_SUFFIX), safe="")
