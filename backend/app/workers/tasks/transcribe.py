from celery import shared_task
import os
import json
from app.services.s3_service import s3_service
from app.database import AsyncSessionLocal
from app.models.video_job import VideoJob
from sqlalchemy import select, update
import shutil

@shared_task(bind=True, max_retries=3)
def transcribe_task(self, job_id: str):
    import asyncio
    asyncio.run(_transcribe_async(job_id))

async def _transcribe_async(job_id: str):
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                raise Exception(f"Job {job_id} tidak ditemukan")
            
            temp_dir = f"/app/uploads/{job_id}"
            os.makedirs(temp_dir, exist_ok=True)
            audio_path = os.path.join(temp_dir, "audio.wav")
            
            # Download audio dari MinIO
            await s3_service.download_file(f"temp/{job_id}/audio.wav", audio_path)
            
            # Transkripsi dengan faster-whisper
            from faster_whisper import WhisperModel
            from app.config import settings
            
            model = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")
            segments, info = model.transcribe(audio_path, beam_size=5, word_timestamps=True)
            
            # Simpan hasil transkripsi
            transcript_data = {
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "segments": []
            }
            
            for segment in segments:
                seg_data = {
                    "id": segment.id,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text.strip(),
                    "words": [
                        {"word": word.word, "start": word.start, "end": word.end, "probability": word.probability}
                        for word in (segment.words or [])
                    ]
                }
                transcript_data["segments"].append(seg_data)
            
            # Generate SRT
            srt_path = os.path.join(temp_dir, "subtitle.srt")
            with open(srt_path, "w", encoding="utf-8") as f:
                for seg in transcript_data["segments"]:
                    f.write(f"{seg['id']+1}\n")
                    f.write(f"{_format_time(seg['start'])} --> {_format_time(seg['end'])}\n")
                    f.write(f"{seg['text']}\n\n")
            
            # Upload hasil
            transcript_path = os.path.join(temp_dir, "transcript.json")
            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)
            
            await s3_service.upload_file(transcript_path, f"temp/{job_id}/transcript.json")
            await s3_service.upload_file(srt_path, f"temp/{job_id}/subtitle.srt")
            
            # Trigger scene detection
            from app.workers.tasks.scene_detect import scene_detect_task
            scene_detect_task.delay(str(job_id))
            
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        except Exception as e:
            await db.execute(
                update(VideoJob)
                .where(VideoJob.id == job_id)
                .values(error_message=str(e))
            )
            await db.commit()
            raise self.retry(exc=e, countdown=120)

def _format_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
