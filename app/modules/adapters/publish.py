from dataclasses import dataclass

from app.core.settings import settings
from app.models.article_draft import ArticleDraft


@dataclass(frozen=True)
class PublishResult:
    target_url: str
    response_payload: dict[str, object]


class PublishClient:
    def publish(self, draft: ArticleDraft) -> PublishResult:
        if settings.publish_adapter != "mock":
            raise NotImplementedError(f"Unsupported publish adapter: {settings.publish_adapter}")
        slug = draft.slug or f"draft-{draft.id}"
        return PublishResult(
            target_url=f"{settings.public_base_url.rstrip('/')}/articles/{slug}",
            response_payload={"adapter": "mock", "draft_id": draft.id, "status": "published"},
        )


publish_client = PublishClient()
