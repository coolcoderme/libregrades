import logging

logger = logging.getLogger(__name__)


def queue_task(task, *args, **kwargs):
    """Enqueue a Celery task; log and continue if Redis is unavailable."""
    try:
        task.delay(*args, **kwargs)
    except Exception:
        logger.exception("Failed to queue background task %s", task.name)
