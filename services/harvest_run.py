from datetime import datetime, timedelta

from enums import SourceName
from exceptions import OpenSgLawHarvestHaltError, OpenSgLawHarvestRunError

_STALE_RUN_HOURS = 12
_MAX_CONSECUTIVE_FAILURES = 3
_MAX_DATABASE_BYTES = 10 * 1_024**3


def get_stale_run_cutoff(now: datetime) -> datetime:
    return now - timedelta(hours=_STALE_RUN_HOURS)


def validate_can_start_harvest_run(running_count: int, source: SourceName) -> None:
    if running_count > 0:
        raise OpenSgLawHarvestRunError(
            f"A {source.value} harvest run started in the last {_STALE_RUN_HOURS} hours is still RUNNING"
        )


def validate_can_send_after_failures(consecutive_failure_count: int) -> None:
    if consecutive_failure_count >= _MAX_CONSECUTIVE_FAILURES:
        raise OpenSgLawHarvestHaltError(
            f"{consecutive_failure_count} failures in a row"
        )


def validate_can_store_at_database_size(database_bytes: int) -> None:
    if database_bytes > _MAX_DATABASE_BYTES:
        raise OpenSgLawHarvestHaltError(
            f"The database holds {database_bytes:,} bytes, past the 10 GB halt; Royce rules before anything else is fetched"
        )
