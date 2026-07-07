from datetime import UTC, datetime

import httpx

from app.core.settings import settings


class TelegramClient:
    def send_message(self, recipient: str, message: str) -> dict[str, object]:
        if not settings.telegram_bot_token:
            return {"ok": True, "mock": True, "recipient": recipient, "message": message}

        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        response = httpx.post(
            url,
            json={"chat_id": recipient, "text": message},
            timeout=20,
        )
        response.raise_for_status()
        return dict(response.json())


def build_review_message(article_id: int, title: str) -> str:
    return (
        "Artikel baru siap direview:\n"
        f"Judul: {title}\n"
        f"Review: {settings.public_base_url}/admin/articles/drafts/{article_id}\n"
        "Action: Approve / Edit / Publish / Reject"
    )


telegram_client = TelegramClient()


def utcnow() -> datetime:
    return datetime.now(UTC)
