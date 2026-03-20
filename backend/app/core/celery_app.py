"""Celery application configuration (optional)."""

import os
import logging

logger = logging.getLogger(__name__)

_ASYNC_PROCESSING = os.getenv("ASYNC_PROCESSING", "true").lower() == "true"
_REDIS_URL = os.getenv("REDIS_URL", "")

celery_app = None

if _ASYNC_PROCESSING and _REDIS_URL:
    try:
        from celery import Celery
        
        celery_app = Celery(
            "oral_narratives",
            broker=_REDIS_URL,
            backend=_REDIS_URL,
            include=["app.core.tasks"]
        )

        celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            task_time_limit=3600,
            task_soft_time_limit=3300,
            worker_prefetch_multiplier=1,
            worker_max_tasks_per_child=50,
            task_acks_late=True,
            task_reject_on_worker_lost=True,
            task_default_retry_delay=60,
            task_max_retries=3,
        )

        celery_app.conf.task_routes = {
            "app.core.tasks.process_video_task": {"queue": "video_processing"},
        }
        
        logger.info(f"Celery initialized with Redis: {_REDIS_URL}")
    except ImportError:
        logger.warning("Celery not installed - async processing disabled")
else:
    logger.info("Async processing disabled - using synchronous mode")


def get_celery_app():
    """Get Celery app or None if not configured."""
    return celery_app


def is_async_enabled() -> bool:
    """Check if async processing is enabled."""
    return celery_app is not None
