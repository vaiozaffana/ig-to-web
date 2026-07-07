from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.settings import settings
from app.models.article_draft import ArticleDraft
from app.models.article_review import ArticleReview
from app.models.enums import ComplianceVerdict, ReviewAction, WorkflowStatus
from app.models.instagram_post import InstagramPost
from app.modules.adapters.instagram import instagram_client
from app.modules.adapters.llm import llm_client, run_agent_with_audit
from app.modules.schemas.article_draft_schema import (
    ArticleDraftDetail,
    ArticleDraftOutput,
    ArticleDraftRead,
    ArticleReviewRead,
    ComplianceCheckResult,
    EditDraftRequest,
    GenerateDraftTaskPayload,
    InstagramMediaItem,
    InstagramPostPayload,
    InstagramPostRead,
    ReviseDraftRequest,
    SeoMetadataOutput,
    SyncResponse,
)


class InvalidTransitionError(ValueError):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def markdown_to_html(markdown: str) -> str:
    paragraphs = [part.strip() for part in markdown.split("\n\n") if part.strip()]
    html_parts: list[str] = []
    for paragraph in paragraphs:
        if paragraph.startswith("# "):
            html_parts.append(f"<h1>{paragraph[2:]}</h1>")
        else:
            html_parts.append(f"<p>{paragraph}</p>")
    return "\n".join(html_parts)


def list_instagram_posts(session: Session) -> list[InstagramPostRead]:
    posts = session.exec(select(InstagramPost).order_by(col(InstagramPost.fetched_at).desc())).all()
    return [_instagram_post_read(post) for post in posts]


def list_drafts(session: Session, status: WorkflowStatus | None = None) -> list[ArticleDraftRead]:
    statement = select(ArticleDraft).order_by(col(ArticleDraft.updated_at).desc())
    if status is not None:
        statement = statement.where(ArticleDraft.status == status)
    drafts = session.exec(statement).all()
    return [_article_draft_read(session, draft) for draft in drafts]


def get_draft_detail(session: Session, draft_id: int) -> ArticleDraftDetail:
    draft = session.get(ArticleDraft, draft_id)
    if draft is None:
        raise LookupError("Article draft not found")
    reviews = session.exec(
        select(ArticleReview)
        .where(ArticleReview.article_draft_id == draft_id)
        .order_by(col(ArticleReview.created_at).desc())
    ).all()
    detail = ArticleDraftDetail.model_validate(_article_draft_read(session, draft).model_dump())
    detail.reviews = [ArticleReviewRead.model_validate(review) for review in reviews]
    return detail


def _article_draft_read(session: Session, draft: ArticleDraft) -> ArticleDraftRead:
    payload = ArticleDraftRead.model_validate(draft)
    post = session.get(InstagramPost, draft.instagram_post_id)
    if post is not None:
        payload.source_media_url = post.media_url
        payload.source_media_type = post.media_type
        payload.source_media_items = _media_items_from_post(post)
    return payload


def _instagram_post_read(post: InstagramPost) -> InstagramPostRead:
    payload = InstagramPostRead.model_validate(post)
    payload.media_items = _media_items_from_post(post)
    return payload


def _media_items_from_post(post: InstagramPost) -> list[InstagramMediaItem]:
    raw_items = post.raw_payload_json.get("media_items")
    if isinstance(raw_items, list):
        media_items: list[InstagramMediaItem] = []
        for item in raw_items:
            if isinstance(item, dict):
                media_items.append(InstagramMediaItem.model_validate(item))
        if media_items:
            return media_items
    if post.media_url:
        return [
            InstagramMediaItem(
                id=post.instagram_media_id,
                media_url=post.media_url,
                media_type=post.media_type,
                permalink=post.permalink,
            )
        ]
    return []


def sync_instagram_posts(session: Session, account_id: str, limit: int) -> SyncResponse:
    fetched_posts = instagram_client.fetch_recent_posts(account_id=account_id, limit=limit)
    created = 0
    skipped = 0
    enqueued = 0
    for payload in fetched_posts:
        post = create_instagram_post_if_new(session, payload)
        if post is None:
            skipped += 1
            continue
        created += 1
        enqueued += 1
        from app.modules.tasks.generate_draft import generate_article_draft

        generate_article_draft.delay(
            GenerateDraftTaskPayload(instagram_post_id=post.id or 0).model_dump(mode="json")
        )
    return SyncResponse(
        created_posts=created, skipped_duplicates=skipped, enqueued_generation=enqueued
    )


def create_instagram_post_if_new(
    session: Session,
    payload: InstagramPostPayload,
) -> InstagramPost | None:
    existing = session.exec(
        select(InstagramPost).where(InstagramPost.instagram_media_id == payload.instagram_media_id)
    ).first()
    if existing is not None:
        _refresh_instagram_post_media(existing, payload)
        session.add(existing)
        session.commit()
        return None

    post = InstagramPost(
        instagram_media_id=payload.instagram_media_id,
        permalink=payload.permalink,
        caption=payload.caption,
        hashtags=payload.hashtags,
        media_url=payload.media_url,
        media_type=payload.media_type,
        posted_at=payload.posted_at,
        raw_payload_json=_raw_payload_with_media_items(payload),
        max_retries=settings.task_max_retries,
    )
    session.add(post)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return None
    session.refresh(post)
    return post


def _raw_payload_with_media_items(payload: InstagramPostPayload) -> dict[str, Any]:
    raw_payload_json = dict(payload.raw_payload_json)
    if payload.media_items:
        raw_payload_json["media_items"] = [
            media.model_dump(mode="json") for media in payload.media_items
        ]
    return raw_payload_json


def _refresh_instagram_post_media(
    post: InstagramPost,
    payload: InstagramPostPayload,
) -> None:
    post.permalink = payload.permalink
    post.caption = payload.caption
    post.hashtags = payload.hashtags
    post.media_url = payload.media_url
    post.media_type = payload.media_type
    post.posted_at = payload.posted_at
    post.raw_payload_json = _raw_payload_with_media_items(payload)
    post.updated_at = utcnow()


def generate_article_for_post(
    session: Session,
    payload: GenerateDraftTaskPayload,
) -> ArticleDraft:
    post = session.get(InstagramPost, payload.instagram_post_id)
    if post is None:
        raise LookupError("Instagram post not found")

    if post.status in {
        WorkflowStatus.DRAFT_GENERATING,
        WorkflowStatus.DRAFT_GENERATED,
        WorkflowStatus.WAITING_REVIEW,
        WorkflowStatus.APPROVED,
        WorkflowStatus.PUBLISHED,
    }:
        existing = session.exec(
            select(ArticleDraft).where(ArticleDraft.instagram_post_id == post.id)
        ).first()
        if existing is not None:
            return existing

    try:
        post.status = WorkflowStatus.ASSET_DOWNLOADED
        post.updated_at = utcnow()
        session.add(post)
        session.commit()

        post.status = WorkflowStatus.DRAFT_GENERATING
        post.updated_at = utcnow()
        session.add(post)
        session.commit()

        agent_input = {
            "caption": post.caption,
            "hashtags": post.hashtags,
            "permalink": post.permalink,
            "media_type": post.media_type,
            "media_items": [
                media.model_dump(mode="json") for media in _media_items_from_post(post)
            ],
            "posted_at": post.posted_at.isoformat(),
            "revision_comment": payload.revision_comment,
        }
        article = run_agent_with_audit(
            session=session,
            agent_name="writer_agent",
            input_json=agent_input,
            call=lambda: llm_client.generate_article(agent_input),
            output_schema=ArticleDraftOutput,
        )
        seo = run_agent_with_audit(
            session=session,
            agent_name="seo_agent",
            input_json=article.model_dump(mode="json"),
            call=lambda: llm_client.generate_seo_metadata(article),
            output_schema=SeoMetadataOutput,
        )
        article.meta_title = seo.meta_title
        article.meta_description = seo.meta_description
        article.tags = seo.tags
        article.category = seo.category

        compliance = run_agent_with_audit(
            session=session,
            agent_name="compliance_agent",
            input_json=article.model_dump(mode="json"),
            call=lambda: llm_client.check_compliance(article),
            output_schema=ComplianceCheckResult,
        )

        status = WorkflowStatus.WAITING_REVIEW
        error_message = None
        if compliance.verdict == ComplianceVerdict.NEEDS_REVISION:
            status = WorkflowStatus.NEEDS_REVISION
            error_message = "; ".join(compliance.reasons)
        elif compliance.verdict == ComplianceVerdict.FAIL:
            status = WorkflowStatus.GENERATION_FAILED
            error_message = "; ".join(compliance.reasons)

        draft = session.exec(
            select(ArticleDraft).where(ArticleDraft.instagram_post_id == post.id)
        ).first()
        if draft is None:
            draft = ArticleDraft(
                instagram_post_id=post.id or 0,
                title=article.title,
                slug=article.slug,
                summary=article.summary,
                content_markdown=article.content_markdown,
                content_html=markdown_to_html(article.content_markdown),
                meta_title=article.meta_title,
                meta_description=article.meta_description,
                category=article.category,
                tags=article.tags,
                image_alt_text=article.image_alt_text,
                source_instagram_url=article.source_instagram_url,
                status=status,
                error_message=error_message,
                max_retries=settings.task_max_retries,
            )
        else:
            draft.title = article.title
            draft.slug = article.slug
            draft.summary = article.summary
            draft.content_markdown = article.content_markdown
            draft.content_html = markdown_to_html(article.content_markdown)
            draft.meta_title = article.meta_title
            draft.meta_description = article.meta_description
            draft.category = article.category
            draft.tags = article.tags
            draft.image_alt_text = article.image_alt_text
            draft.source_instagram_url = article.source_instagram_url
            draft.status = status
            draft.error_message = error_message
            draft.updated_at = utcnow()

        post.status = (
            status if status != WorkflowStatus.WAITING_REVIEW else WorkflowStatus.DRAFT_GENERATED
        )
        post.error_message = error_message
        post.updated_at = utcnow()
        session.add(post)
        session.add(draft)
        session.commit()
        session.refresh(draft)

        if draft.status == WorkflowStatus.WAITING_REVIEW:
            from app.modules.tasks.notify import send_review_notification

            send_review_notification.delay({"article_draft_id": draft.id})
        return draft
    except Exception as exc:
        post.status = WorkflowStatus.GENERATION_FAILED
        post.error_message = str(exc)
        post.retry_count += 1
        post.next_retry_at = utcnow() + timedelta(minutes=2**post.retry_count)
        post.updated_at = utcnow()
        session.add(post)
        draft = session.exec(
            select(ArticleDraft).where(ArticleDraft.instagram_post_id == post.id)
        ).first()
        if draft is not None:
            draft.status = WorkflowStatus.GENERATION_FAILED
            draft.error_message = str(exc)
            draft.retry_count += 1
            draft.next_retry_at = post.next_retry_at
            draft.updated_at = utcnow()
            session.add(draft)
        session.commit()
        raise


def approve_draft(session: Session, draft_id: int, admin_id: str) -> ArticleDraft:
    draft = _get_draft(session, draft_id)
    if draft.status not in {WorkflowStatus.WAITING_REVIEW, WorkflowStatus.NEEDS_REVISION}:
        raise InvalidTransitionError("Only reviewable drafts can be approved")
    draft.status = WorkflowStatus.APPROVED
    draft.approved_by = admin_id
    draft.approved_at = utcnow()
    draft.updated_at = utcnow()
    session.add(draft)
    _add_review(session, draft_id, admin_id, ReviewAction.APPROVE, None)
    session.commit()
    session.refresh(draft)
    return draft


def reject_draft(
    session: Session, draft_id: int, admin_id: str, comment: str | None
) -> ArticleDraft:
    draft = _get_draft(session, draft_id)
    if draft.status in {WorkflowStatus.PUBLISHED, WorkflowStatus.PUBLISHING}:
        raise InvalidTransitionError("Published or publishing drafts cannot be rejected")
    draft.status = WorkflowStatus.REJECTED
    draft.updated_at = utcnow()
    session.add(draft)
    _add_review(session, draft_id, admin_id, ReviewAction.REJECT, comment)
    session.commit()
    session.refresh(draft)
    return draft


def revise_draft(
    session: Session, draft_id: int, admin_id: str, request: ReviseDraftRequest
) -> ArticleDraft:
    draft = _get_draft(session, draft_id)
    if draft.status not in {WorkflowStatus.WAITING_REVIEW, WorkflowStatus.NEEDS_REVISION}:
        raise InvalidTransitionError("Only reviewable drafts can be revised")
    draft.status = WorkflowStatus.NEEDS_REVISION
    draft.updated_at = utcnow()
    session.add(draft)
    _add_review(session, draft_id, admin_id, ReviewAction.REVISE, request.comment)
    session.commit()
    from app.modules.tasks.generate_draft import generate_article_draft

    generate_article_draft.delay(
        GenerateDraftTaskPayload(
            instagram_post_id=draft.instagram_post_id,
            revision_comment=request.comment,
        ).model_dump(mode="json")
    )
    session.refresh(draft)
    return draft


def edit_draft(
    session: Session, draft_id: int, admin_id: str, request: EditDraftRequest
) -> ArticleDraft:
    draft = _get_draft(session, draft_id)
    if draft.status not in {WorkflowStatus.WAITING_REVIEW, WorkflowStatus.APPROVED}:
        raise InvalidTransitionError(
            "Only waiting_review or approved drafts can be manually edited"
        )
    updates = request.model_dump(exclude_unset=True)
    comment = updates.pop("comment", None)
    for key, value in updates.items():
        setattr(draft, key, value)
    if "content_markdown" in updates and "content_html" not in updates:
        draft.content_html = markdown_to_html(draft.content_markdown)
    draft.updated_at = utcnow()
    session.add(draft)
    _add_review(session, draft_id, admin_id, ReviewAction.EDIT_MANUAL, comment)
    session.commit()
    session.refresh(draft)
    return draft


def mark_retry(
    session: Session,
    draft: ArticleDraft,
    status: WorkflowStatus,
    error_message: str,
) -> None:
    draft.status = status
    draft.error_message = error_message
    draft.retry_count += 1
    draft.next_retry_at = utcnow() + timedelta(minutes=2**draft.retry_count)
    draft.updated_at = utcnow()
    session.add(draft)
    session.commit()


def _get_draft(session: Session, draft_id: int) -> ArticleDraft:
    draft = session.get(ArticleDraft, draft_id)
    if draft is None:
        raise LookupError("Article draft not found")
    return draft


def _add_review(
    session: Session,
    draft_id: int,
    admin_id: str,
    action: ReviewAction,
    comment: str | None,
) -> None:
    session.add(
        ArticleReview(
            article_draft_id=draft_id,
            admin_id=admin_id,
            action=action,
            comment=comment,
        )
    )
