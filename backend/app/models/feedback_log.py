import uuid
from sqlalchemy import Column, ForeignKey, Enum, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class FeedbackAction(str, enum.Enum):
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    ADJUST_TRIM = "adjust_trim"

class FeedbackLog(Base):
    __tablename__ = "feedback_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clip_id = Column(UUID(as_uuid=True), ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(Enum(FeedbackAction), nullable=False)
    comment_text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    clip = relationship("Clip", back_populates="feedback_logs")
    user = relationship("User")
