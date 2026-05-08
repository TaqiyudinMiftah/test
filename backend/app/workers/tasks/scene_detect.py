from celery import shared_task
import os
import json
from app.services.s3_service import s3_service
from app.database import AsyncSessionLocal
from app.models.video_job import VideoJob
from sqlalchemy import select, update
import shutil

@shared_task(bind=True, max_retries=3)
def scene_detect_task(self, job_id: str):
    import asyncio
    asyncio.run(_scene_detect_async(job_id))

async def _scene_detect_async(job_id: str):
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                raise Exception(f"Job {job_id} tidak ditemukan")
            
            temp_dir = f"/app/uploads/{job_id}"
            os.makedirs(temp_dir, exist_ok=True)
            local_path = os.path.join(temp_dir, os.path.basename(job.s3_input_path))
            
            object_name = s3_service.get_object_name_from_path(job.s3_input_path)
            await s3_service.download_file(object_name, local_path)
            
            # Scene detection dengan PySceneDetect
            from scenedetect import open_video, SceneManager
            from scenedetect.detectors import ContentDetector
            from scenedetect.backends import VideoStreamCv2
            from app.config import settings
            
            video = open_video(local_path)
            scene_manager = SceneManager()
            scene_manager.add_detector(
                ContentDetector(threshold=settings.SCENE_DETECT_THRESHOLD, min_scene_len=settings.MIN_SCENE_DURATION)
            )
            scene_manager.detect_scenes(video)
            scene_list = scene_manager.get_scene_list()
            
            scenes = []
            for i, scene in enumerate(scene_list[:settings.MAX_SCENES]):
                start = scene[0].get_seconds()
                end = scene[1].get_seconds()
                duration = end - start
                if duration >= settings.MIN_SCENE_DURATION:
                    scenes.append({
                        "id": i,
                        "start": start,
                        "end": end,
                        "duration": duration,
                        "confidence": 1.0
                    })
            
            # Simpan hasil
            scene_path = os.path.join(temp_dir, "scenes.json")
            with open(scene_path, "w") as f:
                json.dump({"scenes": scenes, "total_scenes": len(scenes)}, f, indent=2)
            
            await s3_service.upload_file(scene_path, f"temp/{job_id}/scenes.json")
            
            # Trigger energy scoring
            from app.workers.tasks.energy_score import energy_score_task
            energy_score_task.delay(str(job_id))
            
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
