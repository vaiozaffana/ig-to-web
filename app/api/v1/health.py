from fastapi import APIRouter
from redis import Redis
from sqlmodel import Session, func, select

from app.core.settings import settings
from app.models.article_draft import ArticleDraft
from app.models.engine import engine, ping_db
from app.models.enums import NotificationStatus, WorkflowStatus
from app.models.notification import Notification
from app.modules.schemas.article_draft_schema import HealthResponse, WorkerStatusResponse
from app.modules.tasks.celery_app import celery_app

router = APIRouter(tags=["health"])


def _ping_redis() -> bool:
    client = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
    return bool(client.ping())


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_status = "ok"
    redis_status = "ok"
    try:
        ping_db()
    except Exception:
        db_status = "error"
    try:
        _ping_redis()
    except Exception:
        redis_status = "error"
    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return HealthResponse(status=overall, db=db_status, redis=redis_status)


@router.get("/worker/status", response_model=WorkerStatusResponse)
def worker_status() -> WorkerStatusResponse:
    redis_ok = False
    worker_ok = False
    try:
        redis_ok = _ping_redis()
        worker_ok = bool(celery_app.control.ping(timeout=1))
    except Exception:
        worker_ok = False

    failed_counts: dict[str, int] = {}
    pending_notifications = 0
    with Session(engine) as session:
        for status in [
            WorkflowStatus.FETCH_FAILED,
            WorkflowStatus.GENERATION_FAILED,
            WorkflowStatus.NOTIFICATION_FAILED,
            WorkflowStatus.PUBLISH_FAILED,
        ]:
            failed_counts[status.value] = session.exec(
                select(func.count()).select_from(ArticleDraft).where(ArticleDraft.status == status)
            ).one()
        pending_notifications = session.exec(
            select(func.count())
            .select_from(Notification)
            .where(Notification.status == NotificationStatus.PENDING)
        ).one()

    return WorkerStatusResponse(
        status="ok" if redis_ok and worker_ok else "degraded",
        worker_ok=worker_ok,
        redis_ok=redis_ok,
        failed_counts=failed_counts,
        pending_notifications=pending_notifications,
        last_beat_at=None,
    )
