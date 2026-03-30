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

    If REDIS_URL points to host `redis` (Docker service name) but DNS lookup fails
    in the current runtime, fallback to `localhost`.
    """
    parsed = urlparse(redis_url)
    hostname = parsed.hostname
    if hostname != "redis":
        return redis_url

    try:
        socket.getaddrinfo(hostname, parsed.port or 6379)
        return redis_url
    except socket.gaierror:
        netloc = parsed.netloc.replace("redis", "localhost", 1)
        fallback_url = urlunparse(parsed._replace(netloc=netloc))
        logger.warning(
            "REDIS_URL host 'redis' is unreachable in current environment. "
            "Fallback to localhost is applied.",
            extra={"original_redis_url": redis_url, "fallback_redis_url": fallback_url},
        )
        return fallback_url


runtime_redis_url = _resolve_runtime_redis_url(settings.redis_url)

celery_app = Celery(
    "v2t",
    broker=runtime_redis_url,
    backend=runtime_redis_url,
)

celery_app.conf.update(
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
