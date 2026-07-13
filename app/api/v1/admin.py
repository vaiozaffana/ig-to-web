from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.api.v1.deps import require_admin_api_key
from app.core.settings import settings
from app.models.enums import WorkflowStatus
from app.models.session import get_session
from app.modules.adapters.instagram import instagram_client
from app.modules.adapters.notification import whatsapp_client
from app.modules.schemas.article_draft_schema import (
    AdminActionResponse,
    ArticleDraftDetail,
    ArticleDraftRead,
    EditDraftRequest,
    FetchInstagramTaskPayload,
    InstagramPostRead,
    IntegrationStatusResponse,
    RejectDraftRequest,
    ReviseDraftRequest,
    SyncResponse,
)
from app.modules.services import review_service
from app.modules.services.draft_service import (
    InvalidTransitionError,
    get_draft_detail,
    list_drafts,
    list_instagram_posts,
    sync_instagram_posts,
)
from app.modules.services.publish_service import publish_approved_draft

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_api_key)])


@router.post("/sync-instagram", response_model=SyncResponse)
def sync_instagram(
    session: Annotated[Session, Depends(get_session)],
    limit: int = Query(default=settings.instagram_limit, ge=1, le=100),
) -> SyncResponse:
    try:
        return sync_instagram_posts(session, account_id=settings.instagram_account_id, limit=limit)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/integrations/instagram/status", response_model=IntegrationStatusResponse)
def get_instagram_integration_status() -> IntegrationStatusResponse:
    return instagram_client.validate_credentials(settings.instagram_account_id)


@router.get("/instagram-posts", response_model=list[InstagramPostRead])
def get_instagram_posts(
    session: Annotated[Session, Depends(get_session)],
) -> list[InstagramPostRead]:
    return list_instagram_posts(session)


@router.get("/articles/drafts", response_model=list[ArticleDraftRead])
def get_article_drafts(
    session: Annotated[Session, Depends(get_session)],
    status_filter: Annotated[WorkflowStatus | None, Query(alias="status")] = None,
) -> list[ArticleDraftRead]:
    return list_drafts(session, status_filter)


@router.get("/articles/drafts/{draft_id}", response_model=ArticleDraftDetail)
def get_article_draft(
    draft_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> ArticleDraftDetail:
    try:
        return get_draft_detail(session, draft_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/articles/drafts/{draft_id}/approve", response_model=AdminActionResponse)
def approve_article_draft(
    draft_id: int,
    session: Annotated[Session, Depends(get_session)],
    admin_id: Annotated[str, Depends(require_admin_api_key)],
) -> AdminActionResponse:
    try:
        draft = review_service.approve(session, draft_id, admin_id)
        return AdminActionResponse(id=draft.id or 0, status=draft.status, message="Draft approved")
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/articles/drafts/{draft_id}/reject", response_model=AdminActionResponse)
def reject_article_draft(
    draft_id: int,
    request: RejectDraftRequest,
    session: Annotated[Session, Depends(get_session)],
    admin_id: Annotated[str, Depends(require_admin_api_key)],
) -> AdminActionResponse:
    try:
        draft = review_service.reject(session, draft_id, admin_id, request.comment)
        return AdminActionResponse(id=draft.id or 0, status=draft.status, message="Draft rejected")
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/articles/drafts/{draft_id}/revise", response_model=AdminActionResponse)
def revise_article_draft(
    draft_id: int,
    request: ReviseDraftRequest,
    session: Annotated[Session, Depends(get_session)],
    admin_id: Annotated[str, Depends(require_admin_api_key)],
) -> AdminActionResponse:
    try:
        draft = review_service.revise(session, draft_id, admin_id, request)
        return AdminActionResponse(
            id=draft.id or 0, status=draft.status, message="Revision requested"
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/articles/drafts/{draft_id}/edit", response_model=AdminActionResponse)
def edit_article_draft(
    draft_id: int,
    request: EditDraftRequest,
    session: Annotated[Session, Depends(get_session)],
    admin_id: Annotated[str, Depends(require_admin_api_key)],
) -> AdminActionResponse:
    try:
        draft = review_service.edit(session, draft_id, admin_id, request)
        return AdminActionResponse(id=draft.id or 0, status=draft.status, message="Draft edited")
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/articles/drafts/{draft_id}/publish", response_model=AdminActionResponse)
def publish_article_draft(
    draft_id: int,
    session: Annotated[Session, Depends(get_session)],
    admin_id: Annotated[str, Depends(require_admin_api_key)],
) -> AdminActionResponse:
    try:
        draft = publish_approved_draft(session, draft_id=draft_id, admin_id=admin_id)
        return AdminActionResponse(id=draft.id or 0, status=draft.status, message="Draft published")
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/sync-instagram/task", response_model=dict[str, object])
def enqueue_sync_instagram() -> dict[str, object]:
    from app.modules.tasks.fetch_instagram import scheduled_fetch_instagram_posts

    payload = FetchInstagramTaskPayload(
        account_id=settings.instagram_account_id,
        limit=settings.instagram_limit,
    )
    task = scheduled_fetch_instagram_posts.delay(payload.model_dump(mode="json"))
    return {"task_id": task.id, "status": "queued"}


@router.get("/whatsapp/status")
def get_whatsapp_status() -> dict[str, object]:
    """Check status koneksi WhatsApp Baileys."""
    is_connected = whatsapp_client.is_connected()
    return {
        "connected": is_connected,
        "service_url": settings.whatsapp_service_url,
        "message": "Connected" if is_connected else "Not connected. Scan QR code via /admin/whatsapp/qr"
    }


@router.get("/whatsapp/qr")
def get_whatsapp_qr() -> dict[str, object]:
    """Dapatkan QR code untuk pairing WhatsApp (jika belum connected)."""
    if whatsapp_client.is_connected():
        return {"status": "already_connected", "message": "WhatsApp sudah terkoneksi"}
    
    qr_code = whatsapp_client.get_qr_code()
    
    if not qr_code:
        return {
            "status": "no_qr_available",
            "message": "QR code tidak tersedia. Restart WhatsApp service atau tunggu beberapa detik."
        }
    
    return {
        "status": "qr_available",
        "qr": qr_code,
        "message": "Scan QR code dengan WhatsApp di HP Anda: Settings → Linked Devices → Link a Device"
    }


@router.get("/whatsapp/groups")
def get_whatsapp_groups() -> dict[str, object]:
    """Dapatkan list group WhatsApp yang terhubung."""
    if not whatsapp_client.is_connected():
        return {
            "status": "not_connected",
            "message": "WhatsApp belum terkoneksi. Scan QR code terlebih dahulu.",
            "groups": []
        }
    
    groups = whatsapp_client.list_groups()
    
    return {
        "status": "ok",
        "count": len(groups),
        "groups": groups,
        "message": f"Found {len(groups)} groups. Salin 'id' group yang diinginkan ke WHATSAPP_GROUP_ID"
    }
