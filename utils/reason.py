from exceptions import OpenSgLawReasonError


def validate_can_record_reason(reason: str, change: str, example: str) -> None:
    if not reason.strip():
        raise OpenSgLawReasonError(f"{change} needs a reason, such as {example}")
