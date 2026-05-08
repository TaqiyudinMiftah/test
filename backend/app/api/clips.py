from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
import uuid
from app.database import get_db
from app.logger import get_logger
from app.auth.dependencies import get_current_user
from app.auth.rbac import require_editor
from app.models.user import User
from app.models.clip import Clip, ClipDecision
from app.models.feedback_log import FeedbackLog, FeedbackAction
from app.schemas.job import ClipResponse, ClipDecisionRequest, FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/api/v1/clips", tags=["Clips"])
logger = get_logger("api.clips")

@router.get("", response_model=List[ClipResponse])
@require_editor
async def list_clips(
    decision: ClipDecision = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"List clips request oleh {current_user.email}, filter: {decision}")
    query = select(Clip)
    if decision:
        query = query.where(Clip.editor_decision == decision)
    query = query.order_by(desc(Clip.created_at)).limit(limit).offset(offset)
    
    result = await db.execute(query)
    clips = result.scalars().all()
    logger.info(f"Menampilkan {len(clips)} klip")
    return clips

@router.post("/{clip_id}/decision", response_model=ClipResponse)
@require_editor
async def update_clip_decision(
    clip_id: uuid.UUID,
    request: ClipDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Update decision clip {clip_id} oleh {current_user.email}: {request.decision}")
    result = await db.execute(select(Clip).where(Clip.id == clip_id))
    clip = result.scalar_one_or_none()
    
    if not clip:
        logger.warning(f"Clip {clip_id} tidak ditemukan")
        raise HTTPException(status_code=404, detail="Klip tidak ditemukan")
    
    clip.editor_decision = request.decision
    if request.start_time is not None:
        clip.start_time = request.start_time
    if request.end_time is not None:
        clip.end_time = request.end_time
    
    await db.commit()
    await db.refresh(clip)
    logger.info(f"Decision clip {clip_id} diupdate ke {request.decision}")
    return clip

@router.post("/{clip_id}/feedback", response_model=FeedbackResponse)
@require_editor
async def add_feedback(
    clip_id: uuid.UUID,
    request: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Add feedback clip {clip_id} oleh {current_user.email}: {request.action}")
    result = await db.execute(select(Clip).where(Clip.id == clip_id))
    clip = result.scalar_one_or_none()
    
    if not clip:
        logger.warning(f"Clip {clip_id} tidak ditemukan untuk feedback")
        raise HTTPException(status_code=404, detail="Klip tidak ditemukan")
    
    try:
        action = FeedbackAction(request.action)
    except ValueError:
        logger.warning(f"Action tidak valid: {request.action}")
        raise HTTPException(status_code=400, detail="Aksi tidak valid")
    
    feedback = FeedbackLog(
        clip_id=clip_id,
        user_id=current_user.id,
        action=action,
        comment_text=request.comment_text
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    logger.info(f"Feedback ditambahkan untuk clip {clip_id}")
    return feedback

@router.get("/feedback", response_model=List[FeedbackResponse])
@require_editor
async def list_feedback(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"List feedback oleh {current_user.email}")
    result = await db.execute(
        select(FeedbackLog)
        .order_by(desc(FeedbackLog.created_at))
        .limit(limit)
        .offset(offset)
    )
    feedbacks = result.scalars().all()
    return feedbacks
