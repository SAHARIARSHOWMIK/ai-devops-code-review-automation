from __future__ import annotations
import logging
from fastapi import BackgroundTasks
from ..core.config import get_settings

logger = logging.getLogger(__name__)


def run_review_background(pull_request_id: int, trigger_event: str) -> None:
    from ..core.database import SessionLocal
    from .review_pipeline import execute_review

    with SessionLocal() as db:
        execute_review(db, pull_request_id, trigger_event)


def enqueue_review(
    background_tasks: BackgroundTasks, pull_request_id: int, trigger_event: str
) -> dict:
    settings = get_settings()
    if settings.demo_mode:
        return {"queued": False, "mode": "inline"}
    if settings.use_celery:
        try:
            from ..workers.celery_app import celery

            if celery is not None:
                result = celery.send_task(
                    "analyze_pull_request", args=[pull_request_id, trigger_event]
                )
                return {"queued": True, "mode": "celery", "task_id": result.id}
        except Exception as exc:
            logger.warning(
                "Celery enqueue failed; using FastAPI background task: %s", exc
            )
    background_tasks.add_task(run_review_background, pull_request_id, trigger_event)
    return {"queued": True, "mode": "fastapi_background"}
