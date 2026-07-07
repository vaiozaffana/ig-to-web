from datetime import UTC, datetime

from sqlmodel import Session

from app.core.settings import settings
from app.models.article_draft import ArticleDraft
from app.models.engine import engine
from app.models.enums import NotificationChannel, NotificationStatus, WorkflowStatus
from app.models.notification import Notification
from app.modules.adapters.notification import build_review_message, telegram_client
from app.modules.schemas.article_draft_schema import NotifyTaskPayload
from app.modules.tasks.celery_app import celery_app


@celery_app.task(name="app.modules.tasks.notify.send_review_notification")
def send_review_notification(payload: dict[str, object]) -> dict[str, object]:
    task_payload = NotifyTaskPayload.model_validate(payload)
    with Session(engine) as session:
        draft = session.get(ArticleDraft, task_payload.article_draft_id)
        if draft is None:
            raise LookupError("Article draft not found")
        message = build_review_message(article_id=draft.id or 0, title=draft.title)
        notification = Notification(
            article_draft_id=draft.id or 0,
            channel=NotificationChannel.TELEGRAM,
            recipient=settings.telegram_admin_chat_id or "mock-admin",
            message=message,
            status=NotificationStatus.PENDING,
        )
        session.add(notification)
        session.commit()
        session.refresh(notification)
        try:
            telegram_client.send_message(notification.recipient, message)
            notification.status = NotificationStatus.SENT
            notification.sent_at = datetime.now(UTC)
            session.add(notification)
            session.commit()
            return {"notification_id": notification.id, "status": notification.status}
        except Exception as exc:
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(exc)
            draft.status = WorkflowStatus.NOTIFICATION_FAILED
            draft.error_message = str(exc)
            session.add(notification)
            session.add(draft)
            session.commit()
            raise
