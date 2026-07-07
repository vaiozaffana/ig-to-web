from sqlmodel import Session

from app.models.engine import engine
from app.modules.schemas.article_draft_schema import GenerateDraftTaskPayload
from app.modules.services.draft_service import generate_article_for_post
from app.modules.tasks.celery_app import celery_app


@celery_app.task(name="app.modules.tasks.generate_draft.generate_article_draft")
def generate_article_draft(payload: dict[str, object]) -> dict[str, object]:
    task_payload = GenerateDraftTaskPayload.model_validate(payload)
    with Session(engine) as session:
        draft = generate_article_for_post(session=session, payload=task_payload)
        return {"article_draft_id": draft.id, "status": draft.status}
