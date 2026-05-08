from celery import shared_task
import os
from app.database import AsyncSessionLocal
from app.models.video_job import VideoJob
from sqlalchemy import select, update

@shared_task(bind=True, max_retries=3)
def subtitle_embed_task(self, job_id: str):
    import asyncio
    asyncio.run(_subtitle_embed_async(job_id))

async def _subtitle_embed_async(job_id: str):
    async with AsyncSessionLocal() as db:
        try:
            # Untuk v1.0, subtitle sudah di-generate sebagai file terpisah
            # Burn-in subtitle bisa ditambahkan di versi berikutnya
            
            # Trigger delivery
            from app.workers.tasks.deliver import deliver_task
            deliver_task.delay(str(job_id))
            
        except Exception as e:
            await db.execute(
                update(VideoJob)
                .where(VideoJob.id == job_id)
                .values(error_message=str(e))
            )
            await db.commit()
            raise self.retry(exc=e, countdown=60)
