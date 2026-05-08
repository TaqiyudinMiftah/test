from celery import shared_task
import os
import subprocess
import json
from app.services.s3_service import s3_service
from app.services.job_service import job_service
from app.database import AsyncSessionLocal
from app.logger import get_logger
from sqlalchemy import select, update
from app.models.video_job import VideoJob, JobStatus
import shutil

logger = get_logger("celery.tasks.ingest")

@shared_task(bind=True, max_retries=3)
def ingest_task(self, job_id: str):
    import asyncio
    logger.info(f"[Job {job_id}] Memulai task ingest")
    asyncio.run(_ingest_async(job_id))

async def _ingest_async(job_id: str):
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"[Job {job_id}] Job tidak ditemukan di database")
                raise Exception(f"Job {job_id} tidak ditemukan")
            
            logger.info(f"[Job {job_id}] Update status ke PROCESSING")
            await db.execute(
                update(VideoJob)
                .where(VideoJob.id == job_id)
                .values(status=JobStatus.PROCESSING)
            )
            await db.commit()
            
            # Download file dari MinIO
            temp_dir = f"/app/uploads/{job_id}"
            os.makedirs(temp_dir, exist_ok=True)
            local_path = os.path.join(temp_dir, os.path.basename(job.s3_input_path))
            
            object_name = s3_service.get_object_name_from_path(job.s3_input_path)
            logger.info(f"[Job {job_id}] Download dari MinIO: {object_name}")
            await s3_service.download_file(object_name, local_path)
            logger.info(f"[Job {job_id}] Download selesai: {local_path}")
            
            # Validasi format
            logger.info(f"[Job {job_id}] Validasi format video")
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=format_name", 
                 "-of", "default=noprint_wrappers=1:nokey=1", local_path],
                capture_output=True, text=True
            )
            format_name = result.stdout.strip()
            logger.info(f"[Job {job_id}] Format: {format_name}")
            
            # Validasi codec video
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0", 
                 "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", local_path],
                capture_output=True, text=True
            )
            video_codec = result.stdout.strip().lower()
            logger.info(f"[Job {job_id}] Codec: {video_codec}")
            
            valid_codecs = ["h264", "hevc", "h265"]
            if video_codec not in valid_codecs:
                logger.error(f"[Job {job_id}] Codec tidak didukung: {video_codec}")
                raise Exception(f"Codec video tidak didukung: {video_codec}")
            
            # Ekstraksi metadata
            logger.info(f"[Job {job_id}] Ekstraksi metadata")
            metadata = job_service.extract_metadata(local_path)
            logger.info(f"[Job {job_id}] Metadata: {json.dumps(metadata, indent=2)}")
            
            await db.execute(
                update(VideoJob)
                .where(VideoJob.id == job_id)
                .values(metadata_json=metadata)
            )
            await db.commit()
            
            # Trigger task selanjutnya
            logger.info(f"[Job {job_id}] Trigger audio_extract_task")
            from app.workers.tasks.audio_extract import audio_extract_task
            audio_extract_task.delay(str(job_id))
            
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            logger.info(f"[Job {job_id}] Ingest selesai")
            
        except Exception as e:
            logger.error(f"[Job {job_id}] Error: {str(e)}", exc_info=True)
            await db.execute(
                update(VideoJob)
                .where(VideoJob.id == job_id)
                .values(status=JobStatus.FAILED, error_message=str(e))
            )
            await db.commit()
            raise self.retry(exc=e, countdown=60)
