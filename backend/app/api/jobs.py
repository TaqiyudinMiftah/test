from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid
import os
from app.database import get_db
from app.logger import get_logger
from app.auth.dependencies import get_current_user
from app.auth.rbac import require_admin, require_editor, require_viewer
from app.models.user import User
from app.models.video_job import VideoJob, JobStatus
from app.models.segment import Segment
from app.models.clip import Clip, ClipDecision
from app.schemas.job import VideoJobResponse, VideoJobListResponse, VideoJobCreate, SegmentResponse, ClipResponse
from app.config import settings
from app.services.s3_service import s3_service
from app.services.job_service import job_service
import shutil

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])
logger = get_logger("api.jobs")

ALLOWED_EXTENSIONS = {'.mp4', '.mov'}
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE

@router.post("", response_model=VideoJobResponse, status_code=status.HTTP_201_CREATED)
@require_viewer
async def create_job(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ext = os.path.splitext(file.filename)[1].lower()
    logger.info(f"Upload request dari user {current_user.email}: {file.filename} ({ext})")
    
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"Format file tidak valid: {ext} oleh user {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Format file tidak didukung. Gunakan: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    job_id = uuid.uuid4()
    temp_path = f"/app/uploads/{job_id}{ext}"
    
    try:
        os.makedirs("/app/uploads", exist_ok=True)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(temp_path)
        logger.info(f"File disimpan: {file.filename} ({file_size} bytes)")
        
        if file_size > MAX_FILE_SIZE:
            os.remove(temp_path)
            logger.warning(f"File terlalu besar: {file_size} bytes (max: {MAX_FILE_SIZE})")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ukuran file melebihi batas maksimum 4GB"
            )
        
        logger.info(f"Uploading ke MinIO: raw/{job_id}{ext}")
        s3_path = await s3_service.upload_file(temp_path, f"raw/{job_id}{ext}")
        logger.info(f"Upload ke MinIO berhasil: {s3_path}")
        
        job = VideoJob(
            id=job_id,
            user_id=current_user.id,
            status=JobStatus.PENDING,
            original_filename=file.filename,
            s3_input_path=s3_path
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        logger.info(f"Job dibuat: {job_id} oleh user {current_user.email}")
        os.remove(temp_path)
        
        return job
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"Gagal upload job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengupload file: {str(e)}"
        )

@router.get("", response_model=List[VideoJobListResponse])
@require_viewer
async def list_jobs(
    status: Optional[JobStatus] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(VideoJob).where(VideoJob.user_id == current_user.id)
    if status:
        query = query.where(VideoJob.status == status)
    query = query.order_by(desc(VideoJob.created_at)).limit(limit).offset(offset)
    
    result = await db.execute(query)
    jobs = result.scalars().all()
    return jobs

@router.get("/{job_id}", response_model=VideoJobResponse)
@require_viewer
async def get_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(VideoJob)
        .where(VideoJob.id == job_id, VideoJob.user_id == current_user.id)
        .options(selectinload(VideoJob.segments), selectinload(VideoJob.clips))
    )
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job tidak ditemukan"
        )
    
    return job

@router.get("/{job_id}/segments", response_model=List[SegmentResponse])
@require_viewer
async def get_job_segments(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(VideoJob).where(VideoJob.id == job_id, VideoJob.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    
    result = await db.execute(
        select(Segment)
        .where(Segment.job_id == job_id)
        .order_by(desc(Segment.llm_total_score))
    )
    segments = result.scalars().all()
    return segments

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_admin
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(VideoJob).where(VideoJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    
    await db.delete(job)
    await db.commit()
    return None
