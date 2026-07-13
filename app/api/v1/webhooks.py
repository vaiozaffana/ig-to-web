import logging

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.core.settings import settings
from app.modules.schemas.article_draft_schema import TelegramWebhookPayload
from app.modules.schemas.whatsapp_webhook_schema import WhatsAppWebhookPayload

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)


@router.post("/telegram")
def telegram_webhook(payload: TelegramWebhookPayload) -> dict[str, object]:
    return {"ok": True, "received_update_id": payload.update_id}


@router.get("/whatsapp", response_class=PlainTextResponse)
def whatsapp_webhook_verify(
    request: Request,
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
) -> str:
    """
    WhatsApp webhook verification endpoint.
    
    Meta akan mengirim GET request dengan query params:
    - hub.mode = "subscribe"
    - hub.verify_token = token yang Anda set di Meta console
    - hub.challenge = string random yang harus di-echo kembali
    
    Endpoint ini harus return hub.challenge jika verify_token cocok.
    """
    logger.info(
        f"WhatsApp webhook verification request: mode={hub_mode}, "
        f"token={hub_verify_token[:10]}..., challenge={hub_challenge[:20]}..."
    )
    
    if hub_mode != "subscribe":
        logger.warning(f"Invalid hub.mode: {hub_mode}")
        raise HTTPException(status_code=400, detail="Invalid hub.mode")
    
    if not settings.whatsapp_verify_token:
        logger.error("WHATSAPP_VERIFY_TOKEN not configured!")
        raise HTTPException(status_code=500, detail="Verify token not configured")
    
    if hub_verify_token != settings.whatsapp_verify_token:
        logger.warning(
            f"Token mismatch: expected {settings.whatsapp_verify_token[:10]}..., "
            f"got {hub_verify_token[:10]}..."
        )
        raise HTTPException(status_code=403, detail="Verify token mismatch")
    
    logger.info("✅ WhatsApp webhook verification successful")
    return hub_challenge


@router.post("/whatsapp")
def whatsapp_webhook(payload: WhatsAppWebhookPayload) -> dict[str, object]:
    """
    WhatsApp webhook endpoint untuk menerima notifikasi dari Meta.
    
    Webhook ini akan menerima:
    - Message status updates (sent, delivered, read, failed)
    - Incoming messages (jika user reply)
    - Other events
    
    Untuk v1, kita hanya log dan acknowledge.
    """
    logger.info(f"WhatsApp webhook received: object={payload.object_type}")
    
    for entry in payload.entry:
        logger.info(f"Processing entry ID: {entry.id}")
        for change in entry.changes:
            logger.info(f"Change field: {change.field}")
            
            if change.field == "messages":
                # Message events (incoming messages, status updates)
                value = change.value
                logger.info(
                    f"Message event: product={value.messaging_product}, "
                    f"metadata={value.metadata}"
                )
                
                # Log message statuses if available
                if value.statuses:
                    for status in value.statuses:
                        logger.info(f"Message status update: {status}")
                
                # Log incoming messages if available
                if value.messages:
                    for message in value.messages:
                        logger.info(f"Incoming message: {message}")
            else:
                logger.info(f"Other event type: {change.field}")
    
    return {"status": "ok", "received": True}
