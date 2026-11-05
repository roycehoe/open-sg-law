from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, Column, DateTime, Text
from sqlmodel import Field, SQLModel

from enums import PublishStatus, SourceName, SsoAccessState


class Source(SQLModel, table=True):
    __tablename__ = "source"  # pyright: ignore[reportAssignmentType] sqlmodel types __tablename__ as a declared_attr
    __table_args__ = (
        CheckConstraint(
            "name IN ("
            + ", ".join(f"'{source_name.value}'" for source_name in SourceName)
            + ")",
            name="ck_source_name",
        ),
        CheckConstraint(
            "publish_status IN ("
            + ", ".join(f"'{publish_status.value}'" for publish_status in PublishStatus)
            + ")",
            name="ck_source_publish_status",
        ),
        CheckConstraint(
            "sso_access_state IS NULL OR sso_access_state IN ("
            + ", ".join(
                f"'{sso_access_state.value}'" for sso_access_state in SsoAccessState
            )
            + ")",
            name="ck_source_sso_access_state",
        ),
        CheckConstraint(
            "(name = 'SSO') = (sso_access_state IS NOT NULL)",
            name="ck_source_sso_access_state_only_on_sso",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    name: SourceName = Field(sa_column=Column(Text, nullable=False, unique=True))
    publish_status_reason: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    sso_access_state_reason: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    publish_status_changed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    sso_access_state_changed_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

    publish_status: PublishStatus = Field(sa_column=Column(Text, nullable=False))
    sso_access_state: Optional[SsoAccessState] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
