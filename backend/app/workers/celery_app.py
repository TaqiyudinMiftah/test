from celery import Celery
from app.config import settings

celery_app = Celery(
    "autoclip",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.tasks.ingest",
        "app.workers.tasks.audio_extract",
        "app.workers.tasks.transcribe",
        "app.workers.tasks.scene_detect",
        "app.workers.tasks.energy_score",
        "app.workers.tasks.llm_score",
        "app.workers.tasks.rank_clips",
        "app.workers.tasks.export_clip",
        "app.workers.tasks.embed_subtitle",
        "app.workers.tasks.deliver",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
)

# Import tasks to register them
from app.workers.tasks.ingest import ingest_task
from app.workers.tasks.audio_extract import audio_extract_task
from app.workers.tasks.transcribe import transcribe_task
from app.workers.tasks.scene_detect import scene_detect_task
from app.workers.tasks.energy_score import energy_score_task
from app.workers.tasks.llm_score import llm_score_task
from app.workers.tasks.rank_clips import rank_clips_task
from app.workers.tasks.export_clip import export_clips_task
from app.workers.tasks.embed_subtitle import subtitle_embed_task
from app.workers.tasks.deliver import deliver_task
