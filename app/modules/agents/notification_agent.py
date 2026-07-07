from app.modules.adapters.notification import telegram_client


def send_admin_message(recipient: str, message: str) -> dict[str, object]:
    return telegram_client.send_message(recipient, message)
