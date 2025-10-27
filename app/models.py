from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)  # CHANGED: Integer, not String
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)  # ADDED: For registration
    profession = Column(String, nullable=True)  # ADDED: For registration (not discipline_id)
    specialist_type = Column(String, nullable=True)  # ADDED: For specialist nurses
    hashed_password = Column(String, nullable=False)  # CHANGED: hashed_password, not password_hash

    activities = relationship("UserActivity", back_populates="user")  # ADDED

class UserActivity(Base):  # ADDED: This model is used in your working main.py
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
    discipline_id = Column(String, nullable=False)  # This maps to user.profession
    time_limit = Column(Integer, nullable=False)
    source = Column(String, default="singular")  # 'singular' or 'plural'

    questions = relationship("Question", back_populates="exam")

class Question(Base):
    __tablename__ = "questions"
    id = Column(String, primary_key=True, index=True)
    exam_id = Column(String, ForeignKey("exams.id"), nullable=False)
    text = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)
    correct_idx = Column(Integer, nullable=False)

    exam = relationship("Exam", back_populates="questions")

# Remove StudyNote and ExamResult if they're not in your working main.py
# Or adjust them to match what your working code actually uses