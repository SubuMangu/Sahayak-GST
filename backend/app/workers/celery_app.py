"""Celery app + scheduled jobs (SRS §4 background jobs).

Workers handle heavy/async work off the request path: OCR/LLM extraction at scale, report
generation, and notification fan-out. Celery beat drives the daily due-date reminders (US-03).

The web API runs extraction inline in the MVP for simplicity; flip ``ASYNC_EXTRACTION`` to
dispatch to ``process_invoice`` instead. Tasks here are intentionally thin wrappers around the
same service functions the API uses, so behaviour is identical.
"""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "sahayak",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
)

celery_app.conf.beat_schedule = {
    "daily-due-reminders": {
        "task": "app.workers.tasks.send_due_reminders",
        # 09:00 IST every day (US-03 reminders 3 days before deadlines).
        "schedule": crontab(hour=9, minute=0),
    },
}
