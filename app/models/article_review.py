from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import ReviewAction


class ArticleReview(SQLModel, table=True):
    __tablename__ = "article_reviews"

    id: int | None = Field(default=None, primary_key=True)
    article_draft_id: int = Field(foreign_key="article_drafts.id", index=True)
    admin_id: str
    action: ReviewAction
    comment: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
