from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlmodel import Session, select

from app.models.agent_run import AgentRun
from app.models.article_draft import ArticleDraft
from app.models.article_review import ArticleReview
from app.models.engine import engine
from app.models.enums import NotificationStatus, PublishLogStatus, WorkflowStatus
from app.models.instagram_post import InstagramPost
from app.models.notification import Notification
from app.models.publish_log import PublishLog
from app.modules.adapters import instagram as instagram_adapter
from app.modules.adapters import llm as llm_adapter
from app.modules.adapters import notification as notification_adapter
from app.modules.schemas.article_draft_schema import (
    ArticleDraftOutput,
    GenerateDraftTaskPayload,
    InstagramMediaItem,
    InstagramPostPayload,
    IntegrationStatusResponse,
)
from app.modules.services.draft_service import (
    create_instagram_post_if_new,
    generate_article_for_post,
    list_drafts,
)
from app.modules.tasks.notify import send_review_notification
from app.modules.tasks.retry import retry_failed_jobs


def test_admin_sync_generates_reviewable_draft_and_notification(client, admin_headers) -> None:
    response = client.post("/admin/sync-instagram", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["created_posts"] == 1
    with Session(engine) as session:
        post = session.exec(select(InstagramPost)).one()
        draft = session.exec(select(ArticleDraft)).one()
        agent_runs = session.exec(select(AgentRun)).all()
        notification = session.exec(select(Notification)).one()

    assert post.status == WorkflowStatus.DRAFT_GENERATED
    assert draft.status == WorkflowStatus.WAITING_REVIEW
    assert len(agent_runs) == 3
    assert notification.status == NotificationStatus.SENT


def test_duplicate_instagram_media_id_is_not_reprocessed(client, admin_headers) -> None:
    first = client.post("/admin/sync-instagram", headers=admin_headers)
    second = client.post("/admin/sync-instagram", headers=admin_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["skipped_duplicates"] == 1
    with Session(engine) as session:
        assert len(session.exec(select(InstagramPost)).all()) == 1
        assert len(session.exec(select(ArticleDraft)).all()) == 1


def test_duplicate_instagram_media_id_refreshes_media_metadata_without_new_row() -> None:
    with Session(engine) as session:
        first = create_instagram_post_if_new(
            session,
            InstagramPostPayload(
                instagram_media_id="refresh-media",
                permalink="https://instagram.com/p/refresh-media",
                caption="Single media.",
                hashtags=[],
                media_url="https://example.com/old.jpg",
                media_type="image",
                posted_at=datetime.now(UTC),
            ),
        )
        assert first is not None
        second = create_instagram_post_if_new(
            session,
            InstagramPostPayload(
                instagram_media_id="refresh-media",
                permalink="https://instagram.com/p/refresh-media",
                caption="Carousel media.",
                hashtags=[],
                media_url="https://example.com/new-1.jpg",
                media_type="carousel_album",
                media_items=[
                    InstagramMediaItem(
                        id="new-1",
                        media_url="https://example.com/new-1.jpg",
                        media_type="image",
                    ),
                    InstagramMediaItem(
                        id="new-2",
                        media_url="https://example.com/new-2.mp4",
                        media_type="video",
                    ),
                ],
                posted_at=datetime.now(UTC),
            ),
        )
        refreshed = session.get(InstagramPost, first.id)

    assert second is None
    assert refreshed is not None
    assert refreshed.media_type == "carousel_album"
    assert len(refreshed.raw_payload_json["media_items"]) == 2


def test_approve_then_publish_records_review_and_publish_log(client, admin_headers) -> None:
    client.post("/admin/sync-instagram", headers=admin_headers)
    approve = client.post("/admin/articles/drafts/1/approve", headers=admin_headers)
    publish = client.post("/admin/articles/drafts/1/publish", headers=admin_headers)

    assert approve.status_code == 200
    assert approve.json()["status"] == WorkflowStatus.APPROVED
    assert publish.status_code == 200
    assert publish.json()["status"] == WorkflowStatus.PUBLISHED
    with Session(engine) as session:
        draft = session.get(ArticleDraft, 1)
        reviews = session.exec(select(ArticleReview)).all()
        publish_log = session.exec(select(PublishLog)).one()

    assert draft is not None
    assert draft.status == WorkflowStatus.PUBLISHED
    assert len(reviews) == 2
    assert publish_log.status == PublishLogStatus.SUCCESS


def test_publish_before_approval_is_rejected(client, admin_headers) -> None:
    client.post("/admin/sync-instagram", headers=admin_headers)
    publish = client.post("/admin/articles/drafts/1/publish", headers=admin_headers)

    assert publish.status_code == 409


def test_admin_endpoint_requires_api_key(client) -> None:
    response = client.get("/admin/articles/drafts")

    assert response.status_code == 401


def test_api_prefixed_instagram_status_route_exists(monkeypatch, client, admin_headers) -> None:
    monkeypatch.setattr(
        instagram_adapter.instagram_client,
        "validate_credentials",
        lambda _account_id: IntegrationStatusResponse(
            ok=True,
            provider="instagram",
            account_id="test-account",
            username="test",
            message="ok",
        ),
    )

    response = client.get("/api/admin/integrations/instagram/status", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["provider"] == "instagram"


def test_instagram_carousel_album_children_are_normalized() -> None:
    payload = instagram_adapter.instagram_client._from_graph_item(
        {
            "id": "carousel-1",
            "caption": "Kegiatan sekolah dengan beberapa dokumentasi. #sekolah",
            "media_type": "CAROUSEL_ALBUM",
            "permalink": "https://instagram.com/p/carousel-1",
            "timestamp": "2026-07-07T09:00:00+0000",
            "children": {
                "data": [
                    {
                        "id": "child-image",
                        "media_type": "IMAGE",
                        "media_url": "https://example.com/image.jpg",
                        "permalink": "https://instagram.com/p/carousel-1/1",
                    },
                    {
                        "id": "child-video",
                        "media_type": "VIDEO",
                        "media_url": "https://example.com/video.mp4",
                        "thumbnail_url": "https://example.com/video-thumb.jpg",
                        "permalink": "https://instagram.com/p/carousel-1/2",
                    },
                ]
            },
        }
    )

    assert payload.media_type == "carousel_album"
    assert payload.media_url == "https://example.com/image.jpg"
    assert [media.media_type for media in payload.media_items] == ["image", "video"]
    assert payload.raw_payload_json["media_items"][1]["thumbnail_url"] == (
        "https://example.com/video-thumb.jpg"
    )


def test_draft_response_contains_all_source_media() -> None:
    with Session(engine) as session:
        post = create_instagram_post_if_new(
            session,
            InstagramPostPayload(
                instagram_media_id="carousel-response",
                permalink="https://instagram.com/p/carousel-response",
                caption="Dokumentasi kegiatan sekolah.",
                hashtags=["sekolah"],
                media_url="https://example.com/image.jpg",
                media_type="carousel_album",
                media_items=[
                    InstagramMediaItem(
                        id="child-image",
                        media_url="https://example.com/image.jpg",
                        media_type="image",
                        permalink="https://instagram.com/p/carousel-response/1",
                    ),
                    InstagramMediaItem(
                        id="child-video",
                        media_url="https://example.com/video.mp4",
                        media_type="video",
                        thumbnail_url="https://example.com/video-thumb.jpg",
                        permalink="https://instagram.com/p/carousel-response/2",
                    ),
                ],
                posted_at=datetime.now(UTC),
                raw_payload_json={
                    "media_items": [
                        {
                            "id": "child-image",
                            "media_url": "https://example.com/image.jpg",
                            "media_type": "image",
                            "thumbnail_url": None,
                            "permalink": "https://instagram.com/p/carousel-response/1",
                        },
                        {
                            "id": "child-video",
                            "media_url": "https://example.com/video.mp4",
                            "media_type": "video",
                            "thumbnail_url": "https://example.com/video-thumb.jpg",
                            "permalink": "https://instagram.com/p/carousel-response/2",
                        },
                    ]
                },
            ),
        )
        assert post is not None
        session.add(
            ArticleDraft(
                instagram_post_id=post.id or 0,
                title="Dokumentasi Kegiatan Sekolah",
                slug="dokumentasi-kegiatan-sekolah",
                summary="Dokumentasi kegiatan sekolah dari beberapa media.",
                content_markdown="# Dokumentasi Kegiatan Sekolah\n\nKonten kegiatan sekolah.",
                content_html="<h1>Dokumentasi Kegiatan Sekolah</h1>",
                meta_title="Dokumentasi Kegiatan Sekolah",
                meta_description="Dokumentasi kegiatan sekolah dari beberapa media.",
                category="Berita Sekolah",
                tags=["sekolah"],
                image_alt_text="Dokumentasi kegiatan sekolah",
                source_instagram_url="https://instagram.com/p/carousel-response",
                status=WorkflowStatus.WAITING_REVIEW,
            )
        )
        session.commit()

        data = list_drafts(session)

    assert [media.media_type for media in data[0].source_media_items] == ["image", "video"]
    assert data[0].source_media_items[1].thumbnail_url == "https://example.com/video-thumb.jpg"


def test_invalid_llm_output_marks_generation_failed(monkeypatch) -> None:
    payload = InstagramPostPayload(
        instagram_media_id="bad-output",
        permalink="https://instagram.com/p/bad-output",
        caption="Kegiatan sekolah.",
        hashtags=["sekolah"],
        media_url="https://example.com/image.jpg",
        media_type="image",
        posted_at=datetime.now(UTC),
        raw_payload_json={},
    )

    def invalid_article(_payload: dict[str, object]) -> dict[str, object]:
        return {"title": "x"}

    monkeypatch.setattr(llm_adapter.llm_client, "generate_article", invalid_article)
    with Session(engine) as session:
        post = create_instagram_post_if_new(session, payload)
        assert post is not None
        with pytest.raises(ValidationError):
            generate_article_for_post(
                session,
                GenerateDraftTaskPayload(instagram_post_id=post.id or 0),
            )
        failed_post = session.get(InstagramPost, post.id)
        run = session.exec(select(AgentRun)).one()

    assert failed_post is not None
    assert failed_post.status == WorkflowStatus.GENERATION_FAILED
    assert run.error_message is not None


def test_notification_failure_marks_draft(monkeypatch, client, admin_headers) -> None:
    client.post("/admin/sync-instagram", headers=admin_headers)

    def fail_send(_recipient: str, _message: str) -> dict[str, object]:
        raise RuntimeError("telegram down")

    monkeypatch.setattr(notification_adapter.telegram_client, "send_message", fail_send)
    with pytest.raises(RuntimeError):
        send_review_notification({"article_draft_id": 1})

    with Session(engine) as session:
        draft = session.get(ArticleDraft, 1)
        failed = session.exec(
            select(Notification).where(Notification.status == NotificationStatus.FAILED)
        ).one()

    assert draft is not None
    assert draft.status == WorkflowStatus.NOTIFICATION_FAILED
    assert failed.error_message == "telegram down"


def test_retry_uses_existing_row_ids_and_honors_max_retries(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeTask:
        def delay(self, payload: dict[str, object]) -> None:
            calls.append(payload)

    monkeypatch.setattr("app.modules.tasks.retry.generate_article_draft", FakeTask())
    with Session(engine) as session:
        post = InstagramPost(
            instagram_media_id="retry-me",
            permalink="https://instagram.com/p/retry-me",
            caption="Retry post",
            hashtags=[],
            media_url="",
            media_type="image",
            posted_at=datetime.now(UTC),
            status=WorkflowStatus.GENERATION_FAILED,
            retry_count=0,
            max_retries=1,
        )
        exhausted = InstagramPost(
            instagram_media_id="retry-exhausted",
            permalink="https://instagram.com/p/retry-exhausted",
            caption="Retry exhausted",
            hashtags=[],
            media_url="",
            media_type="image",
            posted_at=datetime.now(UTC),
            status=WorkflowStatus.GENERATION_FAILED,
            retry_count=1,
            max_retries=1,
        )
        session.add(post)
        session.add(exhausted)
        session.commit()
        session.refresh(post)

    result = retry_failed_jobs({"max_items": 10})

    assert result["retried"] == 1
    assert calls == [{"instagram_post_id": post.id, "revision_comment": None}]


def test_generate_article_service_accepts_schema_output(monkeypatch) -> None:
    article = ArticleDraftOutput(
        title="Siswa Mengikuti Kegiatan Literasi",
        slug="siswa-mengikuti-kegiatan-literasi",
        summary="Siswa mengikuti kegiatan literasi sekolah dengan antusias.",
        content_markdown="# Siswa Mengikuti Kegiatan Literasi\n\nKegiatan literasi berjalan baik.",
        meta_title="Siswa Mengikuti Kegiatan Literasi",
        meta_description=(
            "Kegiatan literasi sekolah berjalan baik dan menumbuhkan minat baca siswa."
        ),
        category="Berita Sekolah",
        tags=["literasi"],
        image_alt_text="Siswa mengikuti kegiatan literasi",
        source_instagram_url="https://instagram.com/p/literasi",
    )
    monkeypatch.setattr(instagram_adapter.instagram_client, "_fake_posts", lambda _limit: [])
    monkeypatch.setattr(llm_adapter.llm_client, "generate_article", lambda _payload: article)
    with Session(engine) as session:
        post = create_instagram_post_if_new(
            session,
            InstagramPostPayload(
                instagram_media_id="literasi",
                permalink="https://instagram.com/p/literasi",
                caption="Siswa mengikuti kegiatan literasi.",
                hashtags=["literasi"],
                media_url="",
                media_type="image",
                posted_at=datetime.now(UTC),
            ),
        )
        assert post is not None
        draft = generate_article_for_post(
            session,
            GenerateDraftTaskPayload(instagram_post_id=post.id or 0),
        )

    assert draft.status == WorkflowStatus.WAITING_REVIEW
    assert draft.source_instagram_url == "https://instagram.com/p/literasi"
