from datetime import UTC, datetime

from sqlmodel import Session

from app.core.settings import settings
from app.models.article_draft import ArticleDraft
from app.models.engine import engine
from app.models.enums import NotificationChannel, NotificationStatus, WorkflowStatus
from app.models.notification import Notification
from app.modules.adapters.notification import build_review_message, telegram_client, whatsapp_client
from app.modules.schemas.article_draft_schema import NotifyTaskPayload
from app.modules.tasks.celery_app import celery_app


@celery_app.task(name="app.modules.tasks.notify.send_review_notification")
def send_review_notification(payload: dict[str, object]) -> dict[str, object]:
    task_payload = NotifyTaskPayload.model_validate(payload)
    with Session(engine) as session:
        draft = session.get(ArticleDraft, task_payload.article_draft_id)
        if draft is None:
            raise LookupError("Article draft not found")
        
        # Get Instagram post untuk info tambahan
        from app.models.instagram_post import InstagramPost
        instagram_post = session.get(InstagramPost, draft.instagram_post_id)
        
        # Build message dengan info lengkap
        message = build_review_message(
            article_id=draft.id or 0,
            title=draft.title,
            timestamp=instagram_post.posted_at if instagram_post else None,
            instagram_username=instagram_post.username if instagram_post else None,
            category=draft.category,
        )
        
        # Determine WhatsApp recipient based on mode
        if settings.whatsapp_notification_mode == "group":
            whatsapp_recipient = settings.whatsapp_group_id
        else:
            whatsapp_recipient = settings.whatsapp_admin_phone
        
        attempts = [
            (
                NotificationChannel.WHATSAPP,
                whatsapp_recipient,
                whatsapp_client.send_message,
            ),
            (
                NotificationChannel.TELEGRAM,
                settings.telegram_admin_chat_id or "mock-admin",
                telegram_client.send_message,
            ),
        ]
        errors: list[str] = []
        for channel, recipient, sender in attempts:
            notification = Notification(
                article_draft_id=draft.id or 0,
                channel=channel,
                recipient=recipient,
                message=message,
                status=NotificationStatus.PENDING,
            )
            session.add(notification)
            session.commit()
            session.refresh(notification)
            try:
                sender(notification.recipient, message)
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.now(UTC)
                session.add(notification)
                session.commit()
                return {
                    "notification_id": notification.id,
                    "channel": notification.channel,
                    "status": notification.status,
                }
            except Exception as exc:
                error_message = str(exc)
                errors.append(f"{channel}: {error_message}")
                notification.status = NotificationStatus.FAILED
                notification.error_message = error_message
                session.add(notification)
                session.commit()

        combined_error = "; ".join(errors)
        draft.status = WorkflowStatus.NOTIFICATION_FAILED
        draft.error_message = combined_error
        session.add(draft)
        session.commit()
        raise RuntimeError(combined_error)
