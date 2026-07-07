from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    AgentRunStatus,
    ComplianceVerdict,
    NotificationStatus,
    WorkflowStatus,
)


class ArticleDraftOutput(BaseModel):
    title: str = Field(min_length=3)
    slug: str = Field(min_length=3, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    summary: str = Field(min_length=10)
    content_markdown: str = Field(min_length=20)
    meta_title: str = Field(min_length=3, max_length=70)
    meta_description: str = Field(min_length=10, max_length=180)
    category: str = Field(min_length=2)
    tags: list[str] = Field(default_factory=list)
    image_alt_text: str = Field(min_length=5)
    source_instagram_url: str


class SeoMetadataOutput(BaseModel):
    meta_title: str = Field(min_length=3, max_length=70)
    meta_description: str = Field(min_length=10, max_length=180)
    tags: list[str] = Field(default_factory=list)
    category: str = Field(min_length=2)


class ComplianceCheckResult(BaseModel):
    verdict: ComplianceVerdict
    reasons: list[str] = Field(default_factory=list)
    flagged_sections: list[str] | None = None


class InstagramMediaItem(BaseModel):
    id: str
    media_url: str = ""
    media_type: str = "image"
    thumbnail_url: str | None = None
    permalink: str | None = None


class InstagramPostPayload(BaseModel):
    instagram_media_id: str
    permalink: str
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    media_url: str = ""
    media_type: str = "image"
    media_items: list[InstagramMediaItem] = Field(default_factory=list)
    posted_at: datetime
    raw_payload_json: dict[str, Any] = Field(default_factory=dict)


class FetchInstagramTaskPayload(BaseModel):
    account_id: str
    limit: int = Field(default=10, ge=1, le=100)


class GenerateDraftTaskPayload(BaseModel):
    instagram_post_id: int
    revision_comment: str | None = None


class NotifyTaskPayload(BaseModel):
    article_draft_id: int


class PublishTaskPayload(BaseModel):
    article_draft_id: int
    admin_id: str


class RetryTaskPayload(BaseModel):
    max_items: int = Field(default=20, ge=1, le=100)


class ReviseDraftRequest(BaseModel):
    comment: str = Field(min_length=3)


class RejectDraftRequest(BaseModel):
    comment: str | None = None


class EditDraftRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3)
    summary: str | None = Field(default=None, min_length=10)
    content_markdown: str | None = Field(default=None, min_length=20)
    content_html: str | None = None
    meta_title: str | None = Field(default=None, min_length=3, max_length=70)
    meta_description: str | None = Field(default=None, min_length=10, max_length=180)
    category: str | None = Field(default=None, min_length=2)
    tags: list[str] | None = None
    image_alt_text: str | None = Field(default=None, min_length=5)
    comment: str | None = None


class AdminActionResponse(BaseModel):
    id: int
    status: WorkflowStatus
    message: str


class InstagramPostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    instagram_media_id: str
    permalink: str
    caption: str
    hashtags: list[str]
    media_url: str
    media_type: str
    media_items: list[InstagramMediaItem] = Field(default_factory=list)
    posted_at: datetime
    fetched_at: datetime
    status: WorkflowStatus
    error_message: str | None = None


class ArticleReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    article_draft_id: int
    admin_id: str
    action: str
    comment: str | None
    created_at: datetime


class ArticleDraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    instagram_post_id: int
    title: str
    slug: str
    summary: str
    content_markdown: str
    content_html: str
    meta_title: str
    meta_description: str
    category: str
    tags: list[str]
    image_alt_text: str
    source_instagram_url: str
    source_media_url: str | None = None
    source_media_type: str | None = None
    source_media_items: list[InstagramMediaItem] = Field(default_factory=list)
    status: WorkflowStatus
    approved_by: str | None
    approved_at: datetime | None
    published_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ArticleDraftDetail(ArticleDraftRead):
    reviews: list[ArticleReviewRead] = Field(default_factory=list)


class AgentRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_name: str
    status: AgentRunStatus
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    article_draft_id: int
    channel: str
    recipient: str
    message: str
    status: NotificationStatus
    sent_at: datetime | None
    error_message: str | None


class HealthResponse(BaseModel):
    status: str
    db: str
    redis: str


class WorkerStatusResponse(BaseModel):
    status: str
    worker_ok: bool
    redis_ok: bool
    failed_counts: dict[str, int]
    pending_notifications: int
    last_beat_at: datetime | None = None


class SyncResponse(BaseModel):
    created_posts: int
    skipped_duplicates: int
    enqueued_generation: int


class IntegrationStatusResponse(BaseModel):
    ok: bool
    provider: str
    account_id: str | None = None
    username: str | None = None
    message: str


class TelegramWebhookPayload(BaseModel):
    update_id: int | None = None
    callback_query: dict[str, Any] | None = None
    message: dict[str, Any] | None = None
