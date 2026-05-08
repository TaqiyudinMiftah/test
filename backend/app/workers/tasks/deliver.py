from celery import shared_task
import os
from app.services.s3_service import s3_service
from app.database import AsyncSessionLocal
from app.models.video_job import VideoJob, JobStatus
from app.models.clip import Clip
from sqlalchemy import select, update

@shared_task(bind=True, max_retries=3)
def deliver_task(self, job_id: str):
    import asyncio
    asyncio.run(_deliver_async(job_id))

async def _deliver_async(job_id: str):
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
            
            # Generate presigned URLs untuk setiap clip
            for clip in clips:
                urls = {}
                for fmt, path in clip.output_paths_json.items():
                    object_name = s3_service.get_object_name_from_path(path)
                    try:
                        url = await s3_service.get_presigned_url(object_name, expiry=3600)
                        urls[fmt] = url
                    except:
                        urls[fmt] = path
                clip.output_paths_json = urls
            
            await db.execute(
                update(VideoJob)
                .where(VideoJob.id == job_id)
                .values(
                    status=JobStatus.DONE,
                    s3_output_prefix=f"output/{job_id}/"
                )
            )
            await db.commit()
            
        except Exception as e:
            await db.execute(
                update(VideoJob)
                .where(VideoJob.id == job_id)
                .values(status=JobStatus.FAILED, error_message=str(e))
            )
            await db.commit()
            raise self.retry(exc=e, countdown=60)
