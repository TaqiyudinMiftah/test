from celery import shared_task
import os
from app.database import AsyncSessionLocal
from app.models.video_job import VideoJob
from app.models.segment import Segment
from app.models.clip import Clip, ClipDecision
from app.config import settings
from sqlalchemy import select, desc, update
from uuid import uuid4

@shared_task(bind=True, max_retries=3)
def rank_clips_task(self, job_id: str):
    import asyncio
    asyncio.run(_rank_clips_async(job_id))

async def _rank_clips_async(job_id: str):
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                raise Exception(f"Job {job_id} tidak ditemukan")
            
            result = await db.execute(
                select(Segment)
                .where(Segment.job_id == job_id)
                .order_by(desc(Segment.llm_total_score))
            )
            segments = result.scalars().all()
            
            if not segments:
                # Skip ke export jika tidak ada segmen
                from app.workers.tasks.export_clip import export_clips_task
                export_clips_task.delay(str(job_id))
                return
            
            # Deduplikasi dengan IoU threshold 0.8
            def calculate_iou(seg1, seg2):
                start_max = max(seg1.start_time, seg2.start_time)
                end_min = min(seg1.end_time, seg2.end_time)
                intersection = max(0, end_min - start_max)
                union = (seg1.end_time - seg1.start_time) + (seg2.end_time - seg2.start_time) - intersection
                return intersection / union if union > 0 else 0
            
            filtered_segments = []
            for seg in segments:
                is_duplicate = False
                for selected in filtered_segments:
                    if calculate_iou(seg, selected) > 0.8:
                        is_duplicate = True
                        break
                if not is_duplicate:
                    filtered_segments.append(seg)
            
            # Pilih top-N
            top_segments = filtered_segments[:settings.TOP_N_CLIPS]
            
            # Insert ke clips
            for seg in top_segments:
                clip = Clip(
                    id=uuid4(),
                    job_id=job_id,
                    segment_id=seg.id,
                    editor_decision=ClipDecision.PENDING,
                    start_time=seg.start_time,
                    end_time=seg.end_time
                )
                db.add(clip)
            
            await db.commit()
            
            # Trigger export
            from app.workers.tasks.export_clip import export_clips_task
            export_clips_task.delay(str(job_id))
            
        except Exception as e:
            await db.execute(
                update(VideoJob)
                .where(VideoJob.id == job_id)
                .values(error_message=str(e))
            )
            await db.commit()
            raise self.retry(exc=e, countdown=60)
