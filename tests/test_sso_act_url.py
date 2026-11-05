from utils.sso_act_url import SsoActPdf, get_sso_act_pdf

_PLAIN_CAPTURE_URL = "https://sso.agc.gov.sg/Act/AA1906?ViewType=Pdf&_=20240202184311"
_ARCHIVE_PLAIN_CAPTURE_URL = (
    f"https://web.archive.org/web/20240716171208id_/{_PLAIN_CAPTURE_URL}"
)
_STAMPLESS_URL = "https://sso.agc.gov.sg/Act/BA1994?ViewType=Pdf"
_BLANK_STAMP_URL = "https://sso.agc.gov.sg/Act/MSA1995?ViewType=Pdf&_"
_REVISED_EDITION_URL = "https://sso.agc.gov.sg/Act-Rev/104/Published/19870330?DocDate=19870330&ViewType=Pdf&_=20201127215314"
_HISTORICAL_URL = "https://sso.agc.gov.sg/Act/CLTPA1955/Historical/20140310?DocDate=20000701&ValidDate=20140310&ViewType=Pdf&_=20181004162547"
_POINT_IN_TIME_URL = (
    "https://sso.agc.gov.sg/Act/AA1906?ValidDate=20211231&ViewType=Pdf&_=20240202184311"
)


def test_a_plain_capture_gives_its_code_and_stamp() -> None:
    assert get_sso_act_pdf(_PLAIN_CAPTURE_URL) == SsoActPdf(
        sso_code="AA1906", version_stamp="20240202184311"
    )


def test_a_capture_with_no_stamp_gives_no_stamp() -> None:
    assert get_sso_act_pdf(_STAMPLESS_URL) == SsoActPdf(
        sso_code="BA1994", version_stamp=None
    )


def test_a_blank_stamp_gives_no_stamp() -> None:
    assert get_sso_act_pdf(_BLANK_STAMP_URL) == SsoActPdf(
        sso_code="MSA1995", version_stamp=None
    )


def test_a_revised_edition_is_not_a_current_act_pdf() -> None:
    assert get_sso_act_pdf(_REVISED_EDITION_URL) is None


def test_a_historical_version_is_not_a_current_act_pdf() -> None:
    assert get_sso_act_pdf(_HISTORICAL_URL) is None


def test_a_point_in_time_query_is_not_a_current_act_pdf() -> None:
    assert get_sso_act_pdf(_POINT_IN_TIME_URL) is None


def test_an_archive_wrapped_url_reads_as_its_tail() -> None:
    assert get_sso_act_pdf(_ARCHIVE_PLAIN_CAPTURE_URL) == get_sso_act_pdf(
        _PLAIN_CAPTURE_URL
    )
