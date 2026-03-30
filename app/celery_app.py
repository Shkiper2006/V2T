from celery import Celery
from kombu import Queue

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "v2t",
    broker=settings.redis_url,
    backend=settings.redis_url,
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
