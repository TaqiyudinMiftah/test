import uuid
from sqlalchemy import Column, ForeignKey, Text, Float, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Segment(Base):
    __tablename__ = "segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("video_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    transcript_text = Column(Text)
    scene_confidence = Column(Float, default=0)
    energy_score = Column(Float, default=0)
    llm_completeness = Column(Float, default=0)
    llm_relevance = Column(Float, default=0)
    llm_engagement = Column(Float, default=0)
    llm_clarity = Column(Float, default=0)
    llm_emotion = Column(Float, default=0)
    llm_total_score = Column(Float, default=0, index=True)
    llm_reasoning = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    job = relationship("VideoJob", back_populates="segments")
    clip = relationship("Clip", back_populates="segment", uselist=False)
