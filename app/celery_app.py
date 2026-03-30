import logging
import socket
from urllib.parse import urlparse, urlunparse

from celery import Celery
from kombu import Queue

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def _resolve_runtime_redis_url(redis_url: str) -> str:
    """
    Resolve Redis URL for mixed local/docker runs.

    If REDIS_URL points to non-local host but DNS lookup fails in the current
    runtime, fallback to `localhost`.
    """
    parsed = urlparse(redis_url)
    hostname = parsed.hostname
    if hostname in {None, "localhost", "127.0.0.1"}:
        return redis_url

    try:
        socket.getaddrinfo(hostname, parsed.port or 6379)
        return redis_url
    except socket.gaierror:
        netloc = parsed.netloc.replace(hostname, "localhost", 1)
        fallback_url = urlunparse(parsed._replace(netloc=netloc))
        logger.warning(
            "REDIS_URL host is unreachable in current environment. "
            "Fallback to localhost is applied.",
            extra={
                "original_redis_url": redis_url,
                "unreachable_host": hostname,
                "fallback_redis_url": fallback_url,
            },
        )
        return fallback_url


runtime_broker_url = _resolve_runtime_redis_url(settings.celery_broker_url or settings.redis_url)
runtime_result_backend = _resolve_runtime_redis_url(settings.celery_result_backend or settings.redis_url)

celery_app = Celery(
    "v2t",
    broker=runtime_broker_url,
    backend=runtime_result_backend,
)

celery_app.conf.update(
    broker_url=runtime_broker_url,
    result_backend=runtime_result_backend,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_default_queue="transcription",
    task_queues=(
        Queue("transcription"),
        Queue("transcription_low"),
        Queue("transcription_normal"),
        Queue("transcription_high"),
        Queue("transcription_business"),
    ),
    task_routes={
        "app.tasks.transcription.process_voice": {"queue": "transcription_normal"},
    },
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.tasks"])
