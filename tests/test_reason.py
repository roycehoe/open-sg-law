import pytest

from exceptions import OpenSgLawReasonError
from utils.reason import validate_can_record_reason


def test_a_blank_reason_is_refused_with_the_change_and_an_example() -> None:
    with pytest.raises(
        OpenSgLawReasonError,
        match="A clear needs a reason, such as the date of a reply",
    ):
        validate_can_record_reason(" ", "A clear", "the date of a reply")


def test_a_written_reason_is_accepted() -> None:
    validate_can_record_reason("Letter of 3 November 2026", "A clear", "a date")
