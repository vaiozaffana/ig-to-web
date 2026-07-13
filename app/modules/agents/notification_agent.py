import logging

from app.core.settings import settings
from app.modules.adapters.notification import telegram_client, whatsapp_client

logger = logging.getLogger(__name__)


def send_admin_message(recipient: str, message: str) -> dict[str, object]:
    """
    Send notification via WhatsApp, fallback to Telegram if WhatsApp fails.
    
    Logs WhatsApp errors for debugging but doesn't raise to maintain fallback behavior.
    """
    try:
        result = whatsapp_client.send_message(recipient, message)
        logger.info(f"WhatsApp notification sent successfully to {recipient}")
        return result
    except Exception as e:
        logger.warning(
            f"WhatsApp notification failed: {type(e).__name__}: {e}. Falling back to Telegram."
        )
        result = telegram_client.send_message(
            settings.telegram_admin_chat_id or "mock-admin",
            message,
        )
        logger.info(f"Telegram notification sent as fallback")
        return result
