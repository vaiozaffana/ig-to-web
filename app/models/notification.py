from datetime import UTC, datetime

from sqlmodel import Field, SQLModel

from app.models.enums import NotificationChannel, NotificationStatus


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: int | None = Field(default=None, primary_key=True)
    article_draft_id: int = Field(foreign_key="article_drafts.id", index=True)
    channel: NotificationChannel = NotificationChannel.TELEGRAM
    recipient: str
    message: str
    status: NotificationStatus = Field(default=NotificationStatus.PENDING, index=True)
    sent_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
