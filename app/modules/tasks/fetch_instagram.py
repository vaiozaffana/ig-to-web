from sqlmodel import Session

from app.core.settings import settings
from app.models.engine import engine
from app.modules.schemas.article_draft_schema import FetchInstagramTaskPayload
from app.modules.services.draft_service import sync_instagram_posts
from app.modules.tasks.celery_app import celery_app


@celery_app.task(name="app.modules.tasks.fetch_instagram.scheduled_fetch_instagram_posts")
def scheduled_fetch_instagram_posts(payload: dict[str, object] | None = None) -> dict[str, int]:
    task_payload = FetchInstagramTaskPayload.model_validate(
        payload or {"account_id": settings.instagram_account_id, "limit": settings.instagram_limit}
    )
    with Session(engine) as session:
        result = sync_instagram_posts(
            session=session,
            account_id=task_payload.account_id,
            limit=task_payload.limit,
        )
        return result.model_dump()
