"""Optional Celery worker integration.

The API runs jobs inline in DEMO_MODE. Install celery and redis in production,
then start the worker with: celery -A app.workers.celery_app.celery worker -l info
"""

try:
    from celery import Celery
except ImportError:  # pragma: no cover
    Celery = None
from ..core.config import get_settings

settings = get_settings()
celery = (
    Celery("devops_review", broker=settings.redis_url, backend=settings.redis_url)
    if Celery
    else None
)

if celery:

    @celery.task(name="analyze_pull_request")
    def analyze_pull_request(
        pull_request_id: int, trigger_event: str = "queued"
    ) -> int:
        from ..core.database import SessionLocal
        from ..services.review_pipeline import execute_review

        with SessionLocal() as db:
            return execute_review(db, pull_request_id, trigger_event).id
