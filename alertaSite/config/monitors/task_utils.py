"""Helpers for dispatching Celery monitor tasks with a sync fallback."""


def enqueue_task(task, *args, **kwargs):
    """
    Queue a Celery task asynchronously when the broker is available.
    Falls back to running the task inline so checks still work without Redis.
    """
    try:
        return task.delay(*args, **kwargs)
    except Exception:
        return task.run(*args, **kwargs)
