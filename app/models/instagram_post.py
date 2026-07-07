from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import WorkflowStatus


class InstagramPost(SQLModel, table=True):
    __tablename__ = "instagram_posts"

    id: int | None = Field(default=None, primary_key=True)
    instagram_media_id: str = Field(index=True, unique=True)
    permalink: str
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    media_url: str = ""
    media_type: str = "image"
    local_media_url: str | None = None
    posted_at: datetime
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: WorkflowStatus = Field(default=WorkflowStatus.INSTAGRAM_COLLECTED, index=True)
    raw_payload_json: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    error_message: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
