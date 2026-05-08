from celery import shared_task
import os
import subprocess
from app.services.s3_service import s3_service
from app.database import AsyncSessionLocal
from app.models.video_job import VideoJob
from sqlalchemy import select, update
import shutil

@shared_task(bind=True, max_retries=3)
def audio_extract_task(self, job_id: str):
    import asyncio
    asyncio.run(_audio_extract_async(job_id))

async def _audio_extract_async(job_id: str):
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                raise Exception(f"Job {job_id} tidak ditemukan")
            
            temp_dir = f"/app/uploads/{job_id}"
            os.makedirs(temp_dir, exist_ok=True)
            local_path = os.path.join(temp_dir, os.path.basename(job.s3_input_path))
            audio_path = os.path.join(temp_dir, "audio.wav")
            
            object_name = s3_service.get_object_name_from_path(job.s3_input_path)
            await s3_service.download_file(object_name, local_path)
            
            # Ekstrak audio ke WAV 16kHz mono
            subprocess.run([
                "ffmpeg", "-y", "-i", local_path,
                "-vn", "-acodec", "pcm_s16le",
                "-ar", "16000", "-ac", "1",
                "-af", "loudnorm",
                audio_path
            ], check=True, capture_output=True)
            
            # Upload ke MinIO
            s3_audio_path = f"temp/{job_id}/audio.wav"
            await s3_service.upload_file(audio_path, s3_audio_path)
            
            # Trigger transkripsi
            from app.workers.tasks.transcribe import transcribe_task
            transcribe_task.delay(str(job_id))
            
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        except Exception as e:
            await db.execute(
                update(VideoJob)
                .where(VideoJob.id == job_id)
                .values(error_message=str(e))
            )
            await db.commit()
            raise self.retry(exc=e, countdown=60)
