from app.modules.adapters.notification import telegram_client


def send_telegram_notification(recipient: str, message: str) -> dict[str, object]:
    return telegram_client.send_message(recipient, message)
