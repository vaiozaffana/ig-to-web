from app.modules.adapters.instagram import instagram_client
from app.modules.schemas.article_draft_schema import InstagramPostPayload


def get_instagram_posts(account_id: str, limit: int) -> list[InstagramPostPayload]:
    return instagram_client.fetch_recent_posts(account_id=account_id, limit=limit)


def download_media(media_url: str) -> str:
    return media_url
