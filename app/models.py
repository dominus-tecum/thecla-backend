from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import uuid
from sqlalchemy import Date, UniqueConstraint  # Add these if missing
from datetime import date  # Add this if missing

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    profession = Column(String, nullable=True)
    specialist_type = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    
    # ADDED: Premium features column
    premium_features = Column(
        JSON, 
        default={
            "ai_simulation": False,
            "procedure_trainer": False,
            "ai_job_match": False,
            "usmle": False
        },
        server_default='{"ai_simulation": false, "procedure_trainer": false, "ai_job_match": false, "usmle": false}'
    )

    activities = relationship("UserActivity", back_populates="user")
    study_notes = relationship("StudyNote", back_populates="user")  # NEW

class UserActivity(Base):
    __tablename__ = "user_activity"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_type = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON, nullable=True)
    
    user = relationship("User", back_populates="activities")

class Exam(Base):
    __tablename__ = "exams"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    discipline_id = Column(String, nullable=False)
    time_limit = Column(Integer, nullable=False)
    source = Column(String, default="singular")
    is_released = Column(Boolean, default=False)
    release_date = Column(DateTime, nullable=True)

    questions = relationship("Question", back_populates="exam")

class Question(Base):
    __tablename__ = "questions"
    id = Column(String, primary_key=True, index=True)
    exam_id = Column(String, ForeignKey("exams.id"), nullable=False)
    text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)
    correct_idx = Column(Integer, nullable=False)
    rationale = Column(Text, nullable=True)

    exam = relationship("Exam", back_populates="questions")

# NEW: Study Notes Model - COMPLETE
class StudyNote(Base):
    __tablename__ = "study_notes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chapter_id = Column(String, nullable=False)
    chapter_title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=[])
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="study_notes")



    # ============================================================================
# AI USAGE AUDIT MODELS (NEW - SEPARATE FROM EXISTING LOGIC)
# ============================================================================

class DailyUsageTracking(Base):
    __tablename__ = "daily_usage_tracking"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tracking_date = Column(Date, default=date.today, nullable=False)
    
    # Counters
    simulation_count = Column(Integer, default=0)
    procedure_count = Column(Integer, default=0)
    ai_quiz_questions_count = Column(Integer, default=0)
    
    # Premium flag (cached from user data)
    is_premium = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # One record per user per day
    __table_args__ = (
        UniqueConstraint('user_id', 'tracking_date', name='unique_user_daily'),
    )
    
    def __repr__(self):
        return f"<DailyUsageTracking(user_id={self.user_id}, date={self.tracking_date})>"


class RateLimitDecision(Base):
    __tablename__ = "rate_limit_decisions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    decision_time = Column(DateTime, default=datetime.utcnow)
    resource_type = Column(String(20), nullable=False)
    allowed = Column(Boolean, nullable=False)
    reason = Column(String(100), nullable=False)
    current_count = Column(Integer, nullable=False)
    limit_value = Column(Integer)
    
    def __repr__(self):
        return f"<RateLimitDecision(user_id={self.user_id}, resource={self.resource_type}, allowed={self.allowed})>"