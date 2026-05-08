from celery import shared_task
import os
import subprocess
import json
from app.services.s3_service import s3_service
from app.database import AsyncSessionLocal
from app.models.video_job import VideoJob
from app.models.clip import Clip
from app.config import settings
from sqlalchemy import select, update
import shutil

@shared_task(bind=True, max_retries=3)
def export_clips_task(self, job_id: str):
    import asyncio
    asyncio.run(_export_clips_async(job_id))

async def _export_clips_async(job_id: str):
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                raise Exception(f"Job {job_id} tidak ditemukan")
            
            result = await db.execute(
                select(Clip).where(Clip.job_id == job_id)
            )
            clips = result.scalars().all()
            
            if not clips:
                # Skip ke subtitle jika tidak ada clips
                from app.workers.tasks.embed_subtitle import subtitle_embed_task
                subtitle_embed_task.delay(str(job_id))
                return
            
            temp_dir = f"/app/uploads/{job_id}"
            os.makedirs(temp_dir, exist_ok=True)
            local_path = os.path.join(temp_dir, os.path.basename(job.s3_input_path))
            
            object_name = s3_service.get_object_name_from_path(job.s3_input_path)
            await s3_service.download_file(object_name, local_path)
            
            # Download subtitle
            srt_path = os.path.join(temp_dir, "subtitle.srt")
            try:
                await s3_service.download_file(f"temp/{job_id}/subtitle.srt", srt_path)
            except:
                srt_path = None
            
            for clip in clips:
                output_paths = {}
                
                for fmt in settings.OUTPUT_FORMATS_LIST:
                    output_filename = f"clip_{clip.id}_{fmt.replace(':', 'x')}.mp4"
                    output_path = os.path.join(temp_dir, output_filename)
                    
                    # FFmpeg command berdasarkan format
                    if fmt == "9:16":
                        # Portrait: crop center or pad
                        vf = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
                    elif fmt == "1:1":
                        vf = "scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080:(ow-iw)/2:(oh-ih)/2"
                    else:  # 16:9
                        vf = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
                    
                    cmd = [
                        "ffmpeg", "-y", "-i", local_path,
                        "-ss", str(clip.start_time),
                        "-t", str(clip.end_time - clip.start_time),
                        "-vf", vf,
                        "-c:v", "libx264", "-crf", "23", "-preset", "medium",
                        "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart",
                        output_path
                    ]
                    
                    subprocess.run(cmd, check=True, capture_output=True)
                    
                    # Upload
                    s3_output_path = f"output/{job_id}/{output_filename}"
                    await s3_service.upload_file(output_path, s3_output_path)
                    output_paths[fmt] = s3_output_path
                
                clip.output_paths_json = output_paths
            
            await db.commit()
            
            # Trigger subtitle
            from app.workers.tasks.embed_subtitle import subtitle_embed_task
            subtitle_embed_task.delay(str(job_id))
            
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
