import httpx
import pytest
from sqlmodel import SQLModel

from app.core.settings import settings
from app.main import app
from app.models import (
    AgentRun,
    ArticleDraft,
    ArticleReview,
    InstagramPost,
    Notification,
    PublishLog,
)
from app.models.engine import engine, init_db
from app.modules.adapters.instagram import instagram_client
from app.modules.adapters.notification import telegram_client
from app.modules.schemas.article_draft_schema import InstagramMediaItem, InstagramPostPayload
from app.modules.tasks.celery_app import celery_app


class ASGITestClient:
    def __init__(self) -> None:
        self.transport = httpx.ASGITransport(app=app)

    def get(self, url: str, **kwargs: object) -> httpx.Response:
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: object) -> httpx.Response:
        return self._request("POST", url, **kwargs)

    def _request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        import anyio

        async def send_request() -> httpx.Response:
            async with httpx.AsyncClient(
                transport=self.transport,
                base_url="http://testserver",
            ) as client:
                return await client.request(method, url, **kwargs)

        return anyio.run(send_request)


@pytest.fixture(autouse=True)
def clean_db(monkeypatch: pytest.MonkeyPatch) -> None:
    init_db()
    SQLModel.metadata.drop_all(engine)
    init_db()
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    monkeypatch.setattr(instagram_client, "fetch_recent_posts", _fake_instagram_posts)
    monkeypatch.setattr(
        telegram_client,
        "send_message",
        lambda recipient, message: {
            "ok": True,
            "mock": True,
            "recipient": recipient,
            "message": message,
        },
    )


def _fake_instagram_posts(account_id: str, limit: int) -> list[InstagramPostPayload]:
    from datetime import UTC, datetime

    posts = [
        InstagramPostPayload(
            instagram_media_id="test-media-1",
            permalink="https://instagram.com/p/test-media-1",
            caption="Kegiatan market day siswa berlangsung meriah di sekolah. #sekolah #marketday",
            hashtags=["sekolah", "marketday"],
            media_url="https://example.com/test-media-1.jpg",
            media_type="image",
            media_items=[
                InstagramMediaItem(
                    id="test-media-1",
                    media_url="https://example.com/test-media-1.jpg",
                    media_type="image",
                    permalink="https://instagram.com/p/test-media-1",
                )
            ],
            posted_at=datetime.now(UTC),
            raw_payload_json={"source": "test"},
        )
    ]
    return posts[:limit] if account_id is not None else []


@pytest.fixture
def client() -> ASGITestClient:
    return ASGITestClient()


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"X-Admin-API-Key": settings.admin_api_key}


__all__ = [
    "AgentRun",
    "ArticleDraft",
    "ArticleReview",
    "InstagramPost",
    "Notification",
    "PublishLog",
]
