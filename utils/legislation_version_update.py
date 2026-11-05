from dataclasses import dataclass


@dataclass(frozen=True)
class LegislationVersionNewestUpdate:
    id: int
    is_newest: bool
