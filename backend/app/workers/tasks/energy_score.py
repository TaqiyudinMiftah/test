from celery import shared_task
import os
import json
import numpy as np
import cv2
from app.services.s3_service import s3_service
from app.database import AsyncSessionLocal
from app.models.video_job import VideoJob
from app.models.segment import Segment
from sqlalchemy import select, update
import shutil
from uuid import uuid4

@shared_task(bind=True, max_retries=3)
def energy_score_task(self, job_id: str):
    import asyncio
    asyncio.run(_energy_score_async(job_id))

async def _energy_score_async(job_id: str):
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
            await s3_service.download_file(f"temp/{job_id}/audio.wav", audio_path)
            await s3_service.download_file(f"temp/{job_id}/scenes.json", os.path.join(temp_dir, "scenes.json"))
            await s3_service.download_file(f"temp/{job_id}/transcript.json", os.path.join(temp_dir, "transcript.json"))
            
            with open(os.path.join(temp_dir, "scenes.json")) as f:
                scenes_data = json.load(f)
            scenes = scenes_data.get("scenes", [])
            
            with open(os.path.join(temp_dir, "transcript.json")) as f:
                transcript_data = json.load(f)
            transcript_segments = transcript_data.get("segments", [])
            
            # Audio energy analysis
            import wave
            with wave.open(audio_path, 'rb') as wav:
                n_frames = wav.getnframes()
                framerate = wav.getframerate()
                duration = n_frames / framerate
                audio_data = np.frombuffer(wav.readframes(n_frames), dtype=np.int16)
                
                # Normalize
                audio_data = audio_data.astype(np.float32) / 32768.0
                
                # Calculate RMS per scene
                for scene in scenes:
                    start_sample = int(scene["start"] * framerate)
                    end_sample = int(scene["end"] * framerate)
                    segment_audio = audio_data[start_sample:end_sample]
                    if len(segment_audio) > 0:
                        rms = np.sqrt(np.mean(segment_audio**2))
                        scene["audio_energy"] = float(rms)
                    else:
                        scene["audio_energy"] = 0.0
            
            # Motion score dengan optical flow
            cap = cv2.VideoCapture(local_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            for scene in scenes:
                start_frame = int(scene["start"] * fps)
                end_frame = int(scene["end"] * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                
                prev_gray = None
                motion_scores = []
                
                for frame_idx in range(start_frame, min(end_frame, start_frame + int(fps * 2))):
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    if prev_gray is not None:
                        flow = cv2.calcOpticalFlowFarneback(
                            prev_gray, gray, None,
                            pyr_scale=0.5, levels=3, winsize=15,
                            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
                        )
                        magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
                        motion_scores.append(float(np.mean(magnitude)))
                    prev_gray = gray
                
                scene["motion_score"] = float(np.mean(motion_scores)) if motion_scores else 0.0
                scene["energy_score"] = scene["audio_energy"] * 0.5 + scene["motion_score"] * 0.5
            
            cap.release()
            
            # Insert segments ke database
            for scene in scenes:
                transcript_text = ""
                for t_seg in transcript_segments:
                    if t_seg["start"] >= scene["start"] and t_seg["end"] <= scene["end"]:
                        transcript_text += t_seg["text"] + " "
                
                segment = Segment(
                    id=uuid4(),
                    job_id=job_id,
                    start_time=scene["start"],
                    end_time=scene["end"],
                    transcript_text=transcript_text.strip(),
                    scene_confidence=scene.get("confidence", 1.0),
                    energy_score=scene.get("energy_score", 0.0),
                )
                db.add(segment)
            
            await db.commit()
            
            # Trigger LLM scoring
            from app.workers.tasks.llm_score import llm_score_task
            llm_score_task.delay(str(job_id))
            
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
