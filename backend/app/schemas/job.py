from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from app.models.video_job import JobStatus
from app.models.clip import ClipDecision

class VideoJobBase(BaseModel):
    original_filename: str

class VideoJobCreate(VideoJobBase):
    pass

class VideoJobResponse(VideoJobBase):
    id: UUID
    user_id: UUID
    status: JobStatus
    s3_input_path: Optional[str] = None
    metadata_json: Dict[str, Any] = {}
    s3_output_prefix: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VideoJobListResponse(BaseModel):
    id: UUID
    status: JobStatus
    original_filename: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SegmentResponse(BaseModel):
    id: UUID
    job_id: UUID
    start_time: float
    end_time: float
    transcript_text: Optional[str] = None
    scene_confidence: float = 0
    energy_score: float = 0
    llm_completeness: float = 0
    llm_relevance: float = 0
    llm_engagement: float = 0
    llm_clarity: float = 0
    llm_emotion: float = 0
    llm_total_score: float = 0
    llm_reasoning: Optional[str] = None

    class Config:
        from_attributes = True

class ClipResponse(BaseModel):
    id: UUID
    job_id: UUID
    segment_id: Optional[UUID] = None
    editor_decision: ClipDecision
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    output_paths_json: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ClipDecisionRequest(BaseModel):
    decision: ClipDecision
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class FeedbackCreate(BaseModel):
    action: str
    comment_text: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: UUID
    clip_id: UUID
    user_id: Optional[UUID] = None
    action: str
    comment_text: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
