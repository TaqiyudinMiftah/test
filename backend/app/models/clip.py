import uuid
from sqlalchemy import Column, ForeignKey, Enum, JSON, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class ClipDecision(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"

class Clip(Base):
    __tablename__ = "clips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("video_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_id = Column(UUID(as_uuid=True), ForeignKey("segments.id", ondelete="SET NULL"), nullable=True)
    editor_decision = Column(Enum(ClipDecision), default=ClipDecision.PENDING, nullable=False, index=True)
    start_time = Column(Float)
    end_time = Column(Float)
    output_paths_json = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    job = relationship("VideoJob", back_populates="clips")
    segment = relationship("Segment", back_populates="clip")
    feedback_logs = relationship("FeedbackLog", back_populates="clip", cascade="all, delete-orphan")
