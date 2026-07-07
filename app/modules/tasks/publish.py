from sqlmodel import Session

from app.models.engine import engine
from app.modules.schemas.article_draft_schema import PublishTaskPayload
from app.modules.services.publish_service import publish_approved_draft
from app.modules.tasks.celery_app import celery_app


@celery_app.task(name="app.modules.tasks.publish.publish_approved_article")
def publish_approved_article(payload: dict[str, object]) -> dict[str, object]:
    task_payload = PublishTaskPayload.model_validate(payload)
    with Session(engine) as session:
        draft = publish_approved_draft(
            session=session,
            draft_id=task_payload.article_draft_id,
            admin_id=task_payload.admin_id,
        )
        return {"article_draft_id": draft.id, "status": draft.status}
