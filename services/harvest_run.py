from datetime import datetime, timedelta

from enums import SourceName
from exceptions import OpenSgLawHarvestRunError

_STALE_RUN_HOURS = 12


def get_stale_run_cutoff(now: datetime) -> datetime:
    return now - timedelta(hours=_STALE_RUN_HOURS)


def validate_can_start_harvest_run(running_count: int, source: SourceName) -> None:
    if running_count > 0:
        raise OpenSgLawHarvestRunError(
            f"A {source.value} harvest run started in the last {_STALE_RUN_HOURS} hours is still RUNNING"
        )
