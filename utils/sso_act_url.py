from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qsl

_ACT_PATH_MARKER = "/Act/"
_PLAIN_QUERY_NAMES = frozenset({"ViewType", "_"})
_VERSION_STAMP_NAME = "_"


@dataclass(frozen=True)
class SsoActPdf:
    sso_code: str
    version_stamp: Optional[str]


def get_sso_act_pdf(url: str) -> Optional[SsoActPdf]:
    _before, marker, after = url.partition(_ACT_PATH_MARKER)
    if marker == "":
        return None
    sso_code, _question_mark, query = after.partition("?")
    if "/" in sso_code:
        return None
    query_pairs = parse_qsl(query)
    if not {name for name, _value in query_pairs} <= _PLAIN_QUERY_NAMES:
        return None
    return SsoActPdf(
        sso_code=sso_code,
        version_stamp=dict(query_pairs).get(_VERSION_STAMP_NAME),
    )
