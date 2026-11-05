from dataclasses import dataclass
from typing import Optional

from crud.legislation_version import CharacterCountRow

_HIGH_TEXT_SHARE = 0.99
_LOW_TEXT_SHARE = 0.9
_LOWEST_TEXT_SHARE_COUNT = 5


@dataclass(frozen=True)
class VersionTextShare:
    sso_code: str
    text_share: float


@dataclass(frozen=True)
class TextShareFigures:
    overall_text_share: Optional[float]
    versions_under_high_share_count: int
    versions_under_low_share_count: int
    lowest_text_shares: list[VersionTextShare]


def build_text_share_figures(
    character_count_rows: list[CharacterCountRow],
) -> TextShareFigures:
    body_character_count = sum(
        character_count_row.body_character_count
        for character_count_row in character_count_rows
    )
    version_text_shares = sorted(
        (
            VersionTextShare(
                sso_code=character_count_row.sso_code,
                text_share=character_count_row.section_character_count
                / character_count_row.body_character_count,
            )
            for character_count_row in character_count_rows
        ),
        key=lambda version_text_share: (
            version_text_share.text_share,
            version_text_share.sso_code,
        ),
    )
    return TextShareFigures(
        overall_text_share=(
            None
            if body_character_count == 0
            else sum(
                character_count_row.section_character_count
                for character_count_row in character_count_rows
            )
            / body_character_count
        ),
        versions_under_high_share_count=sum(
            version_text_share.text_share < _HIGH_TEXT_SHARE
            for version_text_share in version_text_shares
        ),
        versions_under_low_share_count=sum(
            version_text_share.text_share < _LOW_TEXT_SHARE
            for version_text_share in version_text_shares
        ),
        lowest_text_shares=version_text_shares[:_LOWEST_TEXT_SHARE_COUNT],
    )
