from sqlmodel import Session

from app.modules.schemas.article_draft_schema import GenerateDraftTaskPayload, SyncResponse
from app.modules.services.draft_service import generate_article_for_post, sync_instagram_posts


class InstagramToArticleWorkflow:
    def collect(self, session: Session, account_id: str, limit: int) -> SyncResponse:
        return sync_instagram_posts(session=session, account_id=account_id, limit=limit)

    def generate(self, session: Session, payload: GenerateDraftTaskPayload) -> int:
        draft = generate_article_for_post(session=session, payload=payload)
        return draft.id or 0
