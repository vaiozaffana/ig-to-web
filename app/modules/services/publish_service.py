from datetime import UTC, datetime

from sqlmodel import Session

from app.models.article_draft import ArticleDraft
from app.models.article_review import ArticleReview
from app.models.enums import PublishLogStatus, ReviewAction, WorkflowStatus
from app.models.publish_log import PublishLog
from app.modules.adapters.publish import publish_client
from app.modules.services.draft_service import InvalidTransitionError


def publish_approved_draft(session: Session, draft_id: int, admin_id: str) -> ArticleDraft:
    draft = session.get(ArticleDraft, draft_id)
    if draft is None:
        raise LookupError("Article draft not found")
    if draft.status != WorkflowStatus.APPROVED:
        raise InvalidTransitionError("Draft must be approved before publish")

    draft.status = WorkflowStatus.PUBLISHING
    draft.updated_at = datetime.now(UTC)
    session.add(draft)
    session.commit()

    try:
        result = publish_client.publish(draft)
        draft.status = WorkflowStatus.PUBLISHED
        draft.published_at = datetime.now(UTC)
        draft.updated_at = datetime.now(UTC)
        session.add(draft)
        session.add(
            PublishLog(
                article_draft_id=draft.id or 0,
                target_url=result.target_url,
                status=PublishLogStatus.SUCCESS,
                response_payload=result.response_payload,
            )
        )
        session.add(
            ArticleReview(
                article_draft_id=draft.id or 0,
                admin_id=admin_id,
                action=ReviewAction.PUBLISH,
                comment=None,
            )
        )
        session.commit()
        session.refresh(draft)
        return draft
    except Exception as exc:
        draft.status = WorkflowStatus.PUBLISH_FAILED
        draft.error_message = str(exc)
        draft.retry_count += 1
        draft.updated_at = datetime.now(UTC)
        session.add(draft)
        session.add(
            PublishLog(
                article_draft_id=draft.id or 0,
                target_url="",
                status=PublishLogStatus.FAILED,
                response_payload={},
                error_message=str(exc),
            )
        )
        session.commit()
        raise
