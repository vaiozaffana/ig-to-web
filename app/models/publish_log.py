from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import PublishLogStatus


class PublishLog(SQLModel, table=True):
    __tablename__ = "publish_logs"

    id: int | None = Field(default=None, primary_key=True)
    article_draft_id: int = Field(foreign_key="article_drafts.id", index=True)
    target_url: str
    status: PublishLogStatus
    response_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    published_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_message: str | None = None
