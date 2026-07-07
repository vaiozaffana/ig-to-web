from celery.schedules import crontab

from app.modules.tasks.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "scheduled-fetch-instagram-posts": {
        "task": "app.modules.tasks.fetch_instagram.scheduled_fetch_instagram_posts",
        "schedule": crontab(hour=0, minute=0),
    },
    "retry-failed-jobs": {
        "task": "app.modules.tasks.retry.retry_failed_jobs",
        "schedule": crontab(minute="*/15"),
    },
}
