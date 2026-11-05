from dataclasses import dataclass

from pydantic import ValidationError

from exceptions import OpenSgLawCdxAnswerError
from schemas.cdx_answer import CdxAnswer
from utils.sso_act_url import get_sso_act_pdf

_ORIGINAL_FIELD = "original"
_TIMESTAMP_FIELD = "timestamp"
_DIGEST_FIELD = "digest"


@dataclass(frozen=True)
class CdxCapture:
    original_url: str
    timestamp: str
    digest: str


def _get_field_index(header: list[str], field_name: str) -> int:
    try:
        return header.index(field_name)
    except ValueError as error:
        raise OpenSgLawCdxAnswerError(
            f"The CDX answer has no {field_name} field"
        ) from error


def get_cdx_captures(cdx_answer_text: str) -> list[CdxCapture]:
    try:
        cdx_answer = CdxAnswer.model_validate_json(cdx_answer_text)
    except ValidationError as error:
        raise OpenSgLawCdxAnswerError(
            "The CDX answer is not a JSON list of rows"
        ) from error
    if not cdx_answer.root:
        return []
    header, *cdx_rows = cdx_answer.root
    original_index = _get_field_index(header, _ORIGINAL_FIELD)
    timestamp_index = _get_field_index(header, _TIMESTAMP_FIELD)
    digest_index = _get_field_index(header, _DIGEST_FIELD)
    try:
        return [
            CdxCapture(
                original_url=cdx_row[original_index],
                timestamp=cdx_row[timestamp_index],
                digest=cdx_row[digest_index],
            )
            for cdx_row in cdx_rows
        ]
    except IndexError as error:
        raise OpenSgLawCdxAnswerError(
            "The CDX answer has a row shorter than its header"
        ) from error


def get_latest_act_captures(cdx_captures: list[CdxCapture]) -> list[CdxCapture]:
    sso_code_to_capture: dict[str, CdxCapture] = {}
    for cdx_capture in cdx_captures:
        sso_act_pdf = get_sso_act_pdf(cdx_capture.original_url)
        if sso_act_pdf is None:
            continue
        stored_capture = sso_code_to_capture.get(sso_act_pdf.sso_code)
        if stored_capture is None or cdx_capture.timestamp > stored_capture.timestamp:
            sso_code_to_capture[sso_act_pdf.sso_code] = cdx_capture
    return [sso_code_to_capture[sso_code] for sso_code in sorted(sso_code_to_capture)]
