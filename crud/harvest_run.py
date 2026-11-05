from datetime import datetime

from sqlmodel import Session, col, func, select

from database.harvest_run import HarvestRun
from enums import HarvestRunStatus, SourceName


class CRUDHarvestRun:
    def __init__(self, session: Session):
        self.session = session

    def create(self, harvest_run: HarvestRun) -> None:
        self.session.add(harvest_run)
        self.session.commit()

    # NOTE: commits, unlike the data writes, so a run's row survives a rollback of its data
    def update(self, harvest_run: HarvestRun) -> None:
        self.session.add(harvest_run)
        self.session.commit()

    def get_count_by_source_and_status_and_started_at_after(
        self, source: SourceName, status: HarvestRunStatus, started_after: datetime
    ) -> int:
        statement = (
            select(func.count())
            .select_from(HarvestRun)
            .where(HarvestRun.source == source)
            .where(HarvestRun.status == status)
            .where(col(HarvestRun.started_at) > started_after)
        )
        return self.session.exec(statement).one()
