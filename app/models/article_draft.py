from datetime import UTC, datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import WorkflowStatus


class ArticleDraft(SQLModel, table=True):
    __tablename__ = "article_drafts"

    id: int | None = Field(default=None, primary_key=True)
    instagram_post_id: int = Field(foreign_key="instagram_posts.id", index=True)
    title: str
    slug: str = Field(index=True)
    summary: str
    content_markdown: str
    content_html: str
    meta_title: str
    meta_description: str
    category: str
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    image_alt_text: str
    source_instagram_url: str
    status: WorkflowStatus = Field(default=WorkflowStatus.DRAFT_GENERATED, index=True)
    approved_by: str | None = None
    approved_at: datetime | None = None
    published_at: datetime | None = None
    error_message: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
