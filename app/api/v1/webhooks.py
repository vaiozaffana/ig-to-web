from fastapi import APIRouter

from app.modules.schemas.article_draft_schema import TelegramWebhookPayload

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/telegram")
def telegram_webhook(payload: TelegramWebhookPayload) -> dict[str, object]:
    return {"ok": True, "received_update_id": payload.update_id}
