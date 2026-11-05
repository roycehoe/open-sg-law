from dataclasses import dataclass

from enums import SourceName


@dataclass(frozen=True)
class LegislationUpdate:
    id: int
    title: str
    is_in_newest_listing: bool
    listing_source: SourceName
