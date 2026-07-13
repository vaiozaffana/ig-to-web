from app.modules.adapters.notification import telegram_client, whatsapp_client


def send_whatsapp_notification(recipient: str, message: str) -> dict[str, object]:
    return whatsapp_client.send_message(recipient, message)


def send_telegram_notification(recipient: str, message: str) -> dict[str, object]:
    return telegram_client.send_message(recipient, message)
