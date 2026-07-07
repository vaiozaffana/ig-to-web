from sqlmodel import Session

from app.models.article_draft import ArticleDraft
from app.modules.schemas.article_draft_schema import EditDraftRequest, ReviseDraftRequest
from app.modules.services.draft_service import approve_draft, edit_draft, reject_draft, revise_draft


def approve(session: Session, draft_id: int, admin_id: str) -> ArticleDraft:
    return approve_draft(session, draft_id, admin_id)


def reject(session: Session, draft_id: int, admin_id: str, comment: str | None) -> ArticleDraft:
    return reject_draft(session, draft_id, admin_id, comment)


def revise(
    session: Session, draft_id: int, admin_id: str, request: ReviseDraftRequest
) -> ArticleDraft:
    return revise_draft(session, draft_id, admin_id, request)


def edit(session: Session, draft_id: int, admin_id: str, request: EditDraftRequest) -> ArticleDraft:
    return edit_draft(session, draft_id, admin_id, request)
