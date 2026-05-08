from celery import shared_task
import os
import json
from app.services.s3_service import s3_service
from app.database import AsyncSessionLocal
from app.models.video_job import VideoJob
from app.models.segment import Segment
from app.ai.llm_scorer import llm_scorer
from sqlalchemy import select, update
import shutil

@shared_task(bind=True, max_retries=3)
def llm_score_task(self, job_id: str):
    import asyncio
    asyncio.run(_llm_score_async(job_id))

async def _llm_score_async(job_id: str):
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                raise Exception(f"Job {job_id} tidak ditemukan")
            
            result = await db.execute(
                select(Segment).where(Segment.job_id == job_id)
            )
            segments = result.scalars().all()
            
            if not segments:
                # Skip ke ranking jika tidak ada segmen
                from app.workers.tasks.rank_clips import rank_clips_task
                rank_clips_task.delay(str(job_id))
                return
            
            # Skoring setiap segmen dengan LLM
            for segment in segments:
                if not segment.transcript_text:
                    continue
                
                scores = await llm_scorer.score_segment(
                    transcript=segment.transcript_text,
                    duration=segment.end_time - segment.start_time,
                    video_topic=job.metadata_json.get("title", "Video")
                )
                
                segment.llm_completeness = scores["completeness"]
                segment.llm_relevance = scores["relevance"]
                segment.llm_engagement = scores["engagement"]
                segment.llm_clarity = scores["clarity"]
                segment.llm_emotion = scores["emotion"]
                segment.llm_total_score = (
                    scores["completeness"] * 0.25 +
                    scores["relevance"] * 0.25 +
                    scores["engagement"] * 0.20 +
                    scores["clarity"] * 0.20 +
                    scores["emotion"] * 0.10
                )
                segment.llm_reasoning = scores.get("reasoning", "")
            
            await db.commit()
            
            # Trigger ranking
            from app.workers.tasks.rank_clips import rank_clips_task
            rank_clips_task.delay(str(job_id))
            
        except Exception as e:
            await db.execute(
                update(VideoJob)
                .where(VideoJob.id == job_id)
                .values(error_message=str(e))
            )
            await db.commit()
            raise self.retry(exc=e, countdown=120)
