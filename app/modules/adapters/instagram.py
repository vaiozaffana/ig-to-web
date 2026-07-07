from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.settings import settings
from app.modules.schemas.article_draft_schema import (
    InstagramMediaItem,
    InstagramPostPayload,
    IntegrationStatusResponse,
)

GRAPH_TIMEOUT = httpx.Timeout(10.0, connect=3.0)


def _extract_hashtags(caption: str) -> list[str]:
    return [part.strip("#.,!?:;") for part in caption.split() if part.startswith("#")]


class InstagramAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class InstagramClient:
    graph_version = "v20.0"

    def fetch_recent_posts(self, account_id: str, limit: int) -> list[InstagramPostPayload]:
        if settings.use_fake_instagram:
            return self._fake_posts(limit)
        if not settings.instagram_access_token:
            raise InstagramAPIError("INSTAGRAM_ACCESS_TOKEN belum diisi.")
        self._validate_graph_token_shape(settings.instagram_access_token)
        if not account_id:
            raise InstagramAPIError("INSTAGRAM_ACCOUNT_ID belum diisi.")

        resolved_account_id = self.resolve_media_account_id(account_id)
        url = f"https://graph.facebook.com/{self.graph_version}/{resolved_account_id}/media"
        params: dict[str, str | int] = {
            "fields": (
                "id,caption,media_url,media_type,permalink,timestamp,thumbnail_url,"
                "children{id,media_url,media_type,permalink,thumbnail_url,timestamp}"
            ),
            "limit": limit,
            "access_token": settings.instagram_access_token,
        }
        try:
            response = httpx.get(url, params=params, timeout=GRAPH_TIMEOUT)
        except httpx.HTTPError as exc:
            raise InstagramAPIError(f"Instagram Graph API request failed: {exc}") from exc
        try:
            self._raise_for_graph_error(response)
        except InstagramAPIError as exc:
            if "nonexisting field (media)" in str(exc):
                raise InstagramAPIError(
                    "Credential valid, tetapi account_id ini tidak bisa membaca media Instagram. "
                    "Gunakan Instagram Business/Creator Account ID, atau Facebook Page ID yang "
                    "terhubung ke Instagram Business Account dan token dengan permission "
                    "instagram_basic serta pages_show_list.",
                    status_code=exc.status_code,
                ) from exc
            raise
        data = response.json()
        return [self._from_graph_item(item) for item in data.get("data", [])]

    def validate_credentials(self, account_id: str) -> IntegrationStatusResponse:
        if settings.use_fake_instagram:
            return IntegrationStatusResponse(
                ok=True,
                provider="instagram",
                account_id="fake",
                username="fake-instagram",
                message="Fake Instagram mode aktif. Set USE_FAKE_INSTAGRAM=false untuk data asli.",
            )
        if not settings.instagram_access_token:
            return IntegrationStatusResponse(
                ok=False,
                provider="instagram",
                account_id=account_id or None,
                message="INSTAGRAM_ACCESS_TOKEN belum diisi.",
            )
        token_shape_error = self._graph_token_shape_error(settings.instagram_access_token)
        if token_shape_error:
            return IntegrationStatusResponse(
                ok=False,
                provider="instagram",
                account_id=account_id or None,
                message=token_shape_error,
            )
        if not account_id:
            return IntegrationStatusResponse(
                ok=False,
                provider="instagram",
                account_id=None,
                message="INSTAGRAM_ACCOUNT_ID belum diisi.",
            )

        resolved_account_id = account_id
        try:
            page_status = self._read_page_instagram_account(account_id)
            if page_status:
                resolved_account_id = page_status["id"]

            url = f"https://graph.facebook.com/{self.graph_version}/{resolved_account_id}"
            response = httpx.get(
                url,
                params={
                    "fields": "id,name",
                    "access_token": settings.instagram_access_token,
                },
                timeout=GRAPH_TIMEOUT,
            )
            self._raise_for_graph_error(response)
        except (InstagramAPIError, httpx.HTTPError) as exc:
            return IntegrationStatusResponse(
                ok=False,
                provider="instagram",
                account_id=account_id,
                message=str(exc),
            )

        data = response.json()
        media_error = self._check_media_access(resolved_account_id)
        if media_error:
            return IntegrationStatusResponse(
                ok=False,
                provider="instagram",
                account_id=str(data.get("id") or resolved_account_id),
                username=(page_status or {}).get("username") or data.get("name"),
                message=media_error,
            )
        return IntegrationStatusResponse(
            ok=True,
            provider="instagram",
            account_id=str(data.get("id") or resolved_account_id),
            username=(page_status or {}).get("username") or data.get("name"),
            message="Instagram credential valid.",
        )

    def resolve_media_account_id(self, account_id: str) -> str:
        page_instagram_account = self._read_page_instagram_account(account_id)
        if page_instagram_account:
            return page_instagram_account["id"]
        return account_id

    def _check_media_access(self, account_id: str) -> str | None:
        response = httpx.get(
            f"https://graph.facebook.com/{self.graph_version}/{account_id}/media",
            params={
                "fields": "id",
                "limit": 1,
                "access_token": settings.instagram_access_token,
            },
            timeout=GRAPH_TIMEOUT,
        )
        if response.is_success:
            return None
        try:
            self._raise_for_graph_error(response)
        except InstagramAPIError as exc:
            if "nonexisting field (media)" in str(exc):
                return (
                    "Credential valid, tetapi account_id ini tidak bisa membaca media Instagram. "
                    "Gunakan Instagram Business/Creator Account ID, atau Facebook Page ID yang "
                    "terhubung ke Instagram Business Account dan token dengan permission "
                    "instagram_basic serta pages_show_list."
                )
            return str(exc)
        return None

    def _validate_graph_token_shape(self, token: str) -> None:
        error = self._graph_token_shape_error(token)
        if error:
            raise InstagramAPIError(error)

    def _graph_token_shape_error(self, token: str) -> str | None:
        if token.startswith(("IG", "IGQ")):
            return (
                "INSTAGRAM_ACCESS_TOKEN terlihat seperti token Instagram Login/API, "
                "bukan Meta Graph API access token. Untuk Instagram Graph API, gunakan "
                "Facebook User/Page access token dari Meta app yang punya permission "
                "instagram_basic dan pages_show_list, lalu isi INSTAGRAM_ACCOUNT_ID "
                "dengan Facebook Page ID atau Instagram Business Account ID."
            )
        return None

    def _read_page_instagram_account(self, page_id: str) -> dict[str, str] | None:
        try:
            response = httpx.get(
                f"https://graph.facebook.com/{self.graph_version}/{page_id}",
                params={
                    "fields": "instagram_business_account{id,username,name}",
                    "access_token": settings.instagram_access_token,
                },
                timeout=GRAPH_TIMEOUT,
            )
        except httpx.HTTPError:
            return None
        if not response.is_success:
            return None
        data = response.json()
        account = data.get("instagram_business_account")
        if isinstance(account, dict) and account.get("id"):
            return {
                "id": str(account["id"]),
                "username": str(account.get("username") or account.get("name") or ""),
            }
        return None

    def _raise_for_graph_error(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        try:
            body = response.json()
        except ValueError:
            body = {}
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            message = error.get("message") or response.reason_phrase
            code = error.get("code")
            error_type = error.get("type")
            raise InstagramAPIError(
                f"Instagram Graph API error {response.status_code}"
                f" ({error_type or 'unknown'}, code {code or 'unknown'}): {message}",
                status_code=response.status_code,
            )
        raise InstagramAPIError(
            f"Instagram Graph API error {response.status_code}: {response.reason_phrase}",
            status_code=response.status_code,
        )

    def _from_graph_item(self, item: dict[str, Any]) -> InstagramPostPayload:
        caption = item.get("caption") or ""
        timestamp = item.get("timestamp")
        posted_at = datetime.now(UTC)
        if timestamp:
            normalized_timestamp = timestamp.replace("Z", "+00:00")
            if normalized_timestamp.endswith("+0000"):
                normalized_timestamp = f"{normalized_timestamp[:-5]}+00:00"
            posted_at = datetime.fromisoformat(normalized_timestamp)
        media_items = self._extract_media_items(item)
        raw_payload = dict(item)
        raw_payload["media_items"] = [media.model_dump(mode="json") for media in media_items]
        primary_media_url = media_items[0].media_url if media_items else item.get("media_url") or ""
        return InstagramPostPayload(
            instagram_media_id=str(item["id"]),
            permalink=item.get("permalink") or "",
            caption=caption,
            hashtags=_extract_hashtags(caption),
            media_url=primary_media_url,
            media_type=(item.get("media_type") or "image").lower(),
            media_items=media_items,
            posted_at=posted_at,
            raw_payload_json=raw_payload,
        )

    def _extract_media_items(self, item: dict[str, Any]) -> list[InstagramMediaItem]:
        media_type = str(item.get("media_type") or "image").lower()
        children = item.get("children")
        child_items = children.get("data", []) if isinstance(children, dict) else []
        if media_type == "carousel_album" and isinstance(child_items, list):
            media_items = [
                self._media_item_from_graph(child)
                for child in child_items
                if isinstance(child, dict)
            ]
            return [media for media in media_items if media.media_url or media.thumbnail_url]
        media = self._media_item_from_graph(item)
        return [media] if media.media_url or media.thumbnail_url else []

    def _media_item_from_graph(self, item: dict[str, Any]) -> InstagramMediaItem:
        media_url = item.get("media_url") or item.get("thumbnail_url") or ""
        return InstagramMediaItem(
            id=str(item.get("id") or ""),
            media_url=media_url,
            media_type=str(item.get("media_type") or "image").lower(),
            thumbnail_url=item.get("thumbnail_url"),
            permalink=item.get("permalink"),
        )

    def _fake_posts(self, limit: int) -> list[InstagramPostPayload]:
        now = datetime.now(UTC)
        return [
            InstagramPostPayload(
                instagram_media_id=f"fake-{now.date().isoformat()}",
                permalink="https://instagram.com/p/fake-school-post",
                caption=(
                    "Kegiatan market day siswa berlangsung meriah di sekolah. #sekolah #marketday"
                ),
                hashtags=["sekolah", "marketday"],
                media_url="https://example.com/fake-school-post.jpg",
                media_type="image",
                media_items=[
                    InstagramMediaItem(
                        id=f"fake-{now.date().isoformat()}",
                        media_url="https://example.com/fake-school-post.jpg",
                        media_type="image",
                        permalink="https://instagram.com/p/fake-school-post",
                    )
                ],
                posted_at=now,
                raw_payload_json={"source": "fake"},
            )
        ][:limit]


instagram_client = InstagramClient()
