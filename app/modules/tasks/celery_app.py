from celery import Celery

from app.core.settings import settings

celery_app = Celery(
    "ig_automation",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.modules.tasks.fetch_instagram",
        "app.modules.tasks.generate_draft",
        "app.modules.tasks.notify",
        "app.modules.tasks.publish",
        "app.modules.tasks.retry",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Bangkok",
    enable_utc=True,
    worker_concurrency=settings.worker_concurrency,
    task_track_started=True,
)
