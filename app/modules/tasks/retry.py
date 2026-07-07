from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.models.article_draft import ArticleDraft
from app.models.engine import engine
from app.models.enums import WorkflowStatus
from app.models.instagram_post import InstagramPost
from app.modules.schemas.article_draft_schema import GenerateDraftTaskPayload, RetryTaskPayload
from app.modules.tasks.celery_app import celery_app
from app.modules.tasks.generate_draft import generate_article_draft
from app.modules.tasks.notify import send_review_notification
from app.modules.tasks.publish import publish_approved_article

FAILED_STATUSES = {
    WorkflowStatus.FETCH_FAILED,
    WorkflowStatus.GENERATION_FAILED,
    WorkflowStatus.NOTIFICATION_FAILED,
    WorkflowStatus.PUBLISH_FAILED,
}


@celery_app.task(name="app.modules.tasks.retry.retry_failed_jobs")
def retry_failed_jobs(payload: dict[str, object] | None = None) -> dict[str, int]:
    task_payload = RetryTaskPayload.model_validate(payload or {})
    now = datetime.now(UTC)
    retried = 0
    skipped = 0
    with Session(engine) as session:
        posts = session.exec(
            select(InstagramPost)
            .where(col(InstagramPost.status).in_(FAILED_STATUSES))
            .where(InstagramPost.retry_count < InstagramPost.max_retries)
            .limit(task_payload.max_items)
        ).all()
        for post in posts:
            if post.next_retry_at and post.next_retry_at > now:
                skipped += 1
                continue
            generate_article_draft.delay(
                GenerateDraftTaskPayload(instagram_post_id=post.id or 0).model_dump(mode="json")
            )
            retried += 1

        drafts = session.exec(
            select(ArticleDraft)
            .where(col(ArticleDraft.status).in_(FAILED_STATUSES))
            .where(ArticleDraft.retry_count < ArticleDraft.max_retries)
            .limit(max(task_payload.max_items - retried, 0))
        ).all()
        for draft in drafts:
            if draft.next_retry_at and draft.next_retry_at > now:
                skipped += 1
                continue
            if draft.status == WorkflowStatus.NOTIFICATION_FAILED:
                send_review_notification.delay({"article_draft_id": draft.id})
            elif draft.status == WorkflowStatus.PUBLISH_FAILED and draft.approved_by:
                publish_approved_article.delay(
                    {"article_draft_id": draft.id, "admin_id": draft.approved_by}
                )
            else:
                generate_article_draft.delay(
                    GenerateDraftTaskPayload(instagram_post_id=draft.instagram_post_id).model_dump(
                        mode="json"
                    )
                )
            retried += 1
    return {"retried": retried, "skipped": skipped}
