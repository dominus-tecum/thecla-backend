# At the VERY TOP of main.py (after imports but before app = FastAPI())
import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Then try to import openai ONLY if we have the key
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    print("⚠️ OpenAI module not installed. AI features disabled.")
    OPENAI_AVAILABLE = False
    # Create a dummy openai module to prevent errors
    class DummyOpenAI:
        api_key = None
        class ChatCompletion:
            @staticmethod
            async def acreate(*args, **kwargs):
                raise ImportError("OpenAI not installed")
        class Model:
            @staticmethod
            def list():
                return {"data": []}
    openai = DummyOpenAI()

# Now import your config
try:
    from config import config
    CONFIG_AVAILABLE = True
except ImportError:
    print("⚠️ config.py not found. Using default configuration.")
    CONFIG_AVAILABLE = False
    # Create a simple config class
    class SimpleConfig:
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "800"))
        OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() == "true"
        MAX_AI_QUESTIONS_PER_DAY = int(os.getenv("MAX_AI_QUESTIONS_PER_DAY", "100"))
        AI_QUESTION_TIMEOUT = int(os.getenv("AI_QUESTION_TIMEOUT", "10"))
    
    config = SimpleConfig()

# Set OpenAI API key if available
# Initialize OpenAI client if available
openai_client = None

if OPENAI_AVAILABLE and config.OPENAI_API_KEY and config.OPENAI_API_KEY != "sk-your-actual-openai-api-key-here":
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        print(f"✅ OpenAI client initialized with model: {config.OPENAI_MODEL}")
    except Exception as e:
        print(f"❌ Failed to initialize OpenAI client: {e}")
        openai_client = None
else:
    if not OPENAI_AVAILABLE:
        print("⚠️ OpenAI package not installed. Run: pip install openai")
    elif not config.OPENAI_API_KEY or config.OPENAI_API_KEY == "sk-your-actual-openai-api-key-here":
        print("⚠️ OpenAI API key not configured in .env file")
    print("⚠️ AI quiz features will be disabled")

# Now continue with the rest of your imports
from fastapi import FastAPI, Depends, HTTPException, Body, Query, Request, status
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, create_engine, Boolean, Text, Enum, func
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.sql import case
from passlib.context import CryptContext
from datetime import datetime
import uvicorn
from typing import Optional, List
import hashlib
import secrets
import re  # ADDED: For rationale parsing
import phonenumbers  # ADDED: For phone number validation
from enum import Enum as PyEnum
import uuid  # ADDED: For generating UUIDs
import random  # Add this import
from app.database import get_keamed_db 
from sqlalchemy import text
import json
# ✅ ADD SECURITY IMPORTS
from jose import JWTError, jwt
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# NEW IMPORTS FOR STUDY NOTES
import requests
from bs4 import BeautifulSoup
from app.ai.simulation_service import simulation_service
from app.ai.procedure_service import procedure_service
from datetime import date  # Add this import
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date  # Add 'Date'
from sqlalchemy.ext.declarative import declarative_base

from datetime import date as dtdate
from pydantic import BaseModel, Field




# Database setup
DATABASE_URL = "sqlite:///./theclamed.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

# ✅ SECURITY: CHANGE TO BCrypt (SECURE)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# ✅ ADD ROOT ENDPOINT HERE
@app.get("/")
def read_root():
    return {"message": "TheclaMed API is running!", "status": "healthy"}

# ✅ SECURITY CONFIGURATION
SECRET_KEY = "your-super-secret-key-change-this-in-production-12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 Scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ✅ CORS SECURITY
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ENUMS FOR USER STATUS
class UserStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"  # ✅ ADD THIS LINE

# ✅ TOKEN RESPONSE MODEL
class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    full_name: str
    profession: str
    email: str
    # ADD THIS FIELD:
    premium_features: Optional[dict] = None
    
    class Config:
        from_attributes = True

# STUDY NOTES PYDANTIC MODELS
class StudyNoteCreate(BaseModel):
    chapter_id: str
    chapter_title: str
    content: str
    tags: Optional[List[str]] = []


# 🟢 ADD THIS RIGHT HERE:
class IntelligentExamRequest(BaseModel):
    discipline: str
    question_count: int = 15
    focus_areas: Optional[List[str]] = None



class StudyNoteResponse(BaseModel):
    id: str
    chapter_id: str
    chapter_title: str
    content: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ChapterContent(BaseModel):
    title: str
    content: str
    objectives: List[str]
    url: str

# MODELS - UPDATED USER MODEL WITH STATUS FIELD

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    phone = Column(String, nullable=True)
    profession = Column(String, nullable=True)
    specialist_type = Column(String, nullable=True)
    hashed_password = Column(String)
    status = Column(String, default=UserStatus.PENDING)  # NEW: User approval status
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    role = Column(String, default="user", nullable=False)  # "user" or "admin"
 
    # ✅ ADD THIS EXACTLY HERE:
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
    study_notes = relationship("StudyNote", back_populates="user")  # NEW: Study notes relationship

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
    title = Column(String, index=True)
    discipline_id = Column(String)
    time_limit = Column(Integer)
    source = Column(String, default="singular")
    is_released = Column(Boolean, default=False)
    release_date = Column(DateTime, nullable=True)
    questions = relationship("Question", back_populates="exam")

    # 🟢 ADD THESE 4 LINES RIGHT HERE:
    topic = Column(String, nullable=True)        # "pharmacology", "anatomy"
    subtopic = Column(String, nullable=True)     # "antibiotics", "cardiac"  
    difficulty = Column(String, nullable=True)   # "basic", "intermediate", "advanced"
    concepts = Column(JSON, nullable=True)       # ["mechanism_of_action", "side_effects"]
    
    
class Question(Base):
    __tablename__ = "questions"
    id = Column(String, primary_key=True, index=True)
    exam_id = Column(String, ForeignKey("exams.id"))
    text = Column(String)
    options = Column(JSON)
    correct_idx = Column(Integer)
    rationale = Column(Text, nullable=True)  # NEW: Added rationale column

      # 🟢 ADD THESE 3 MISSING COLUMNS:
    topic = Column(String, nullable=True)
    subtopic = Column(String, nullable=True) 
    difficulty = Column(String, nullable=True)


    exam = relationship("Exam", back_populates="questions")


# DELETE the entire DailyUsageTracking class and recreate it:

class DailyUsageTracking(Base):
    __tablename__ = "daily_usage_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    tracking_date = Column(Date, index=True)  # Use tracking_date, not date
    simulation_count = Column(Integer, default=0)
    procedure_count = Column(Integer, default=0)
    ai_quiz_questions_count = Column(Integer, default=0)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class LimitsSchema(BaseModel):
    simulation: int = Field(ge=0)
    procedure: int = Field(ge=0)
    quiz_question: int = Field(ge=0)




class RateLimitDecision(Base):
    __tablename__ = "rate_limit_decisions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    decision_time = Column(DateTime, default=datetime.utcnow, index=True)
    resource_type = Column(String, index=True)  # 'simulation', 'procedure', 'quiz_question'
    allowed = Column(Boolean, default=True)
    reason = Column(String)
    current_count = Column(Integer, default=0)
    limit_value = Column(Integer, nullable=True)  # null = unlimited (premium)
    
    # Optional: Add relationship
    # user = relationship("User")










# STUDY NOTES MODEL
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

# DROP AND RECREATE TABLES TO ADD NEW COLUMNS
# Base.metadata.drop_all(bind=engine)  # THIS WILL RESET YOUR DATABASE
Base.metadata.create_all(bind=engine)

# UTILS

def update_database_schema():
    """Add missing columns to the database"""
    print("🔄 Updating database schema...")
    
    # This will add any missing columns to your existing tables
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database schema updated successfully!")
    except Exception as e:
        print(f"❌ Error updating schema: {e}")

# Call this function when your app starts
update_database_schema()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def log_activity(db: Session, user_id: int, activity_type: str, details: dict = None):
    activity = UserActivity(
        user_id=user_id,
        activity_type=activity_type,
        details=details
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity





def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()

# ✅ JWT TOKEN FUNCTIONS
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_id(db, user_id=user_id)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.status != UserStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# NEW: DISCIPLINE SYSTEM FUNCTIONS
def get_user_discipline_id(user: User) -> str:
    """
    Determine the discipline_id based on profession and specialist_type
    This is the CORE of our discipline system
    """
    # Specialist nurses use their specific specialty as discipline_id
    if user.profession == "specialist_nurse" and user.specialist_type:
        return user.specialist_type  # icu_nurse, emergency_nurse, neonatal_nurse
    
    # All other professions use their main profession as discipline_id
    return user.profession  # gp, nurse, midwife, lab_tech, physiotherapist

def validate_profession_and_specialty(profession: str, specialist_type: str) -> bool:
    """
    Validate that profession and specialty combinations are valid
    """
    valid_combinations = {
        "specialist_nurse": ["icu_nurse", "emergency_nurse", "neonatal_nurse", "other"]
    }
    
    if profession == "specialist_nurse":
        if not specialist_type:
            return False
        if specialist_type not in valid_combinations["specialist_nurse"]:
            return False
    
    # For non-specialist professions, specialist_type should be empty or None
    if profession != "specialist_nurse" and specialist_type:
        return False
        
    return True

def get_available_professions():
    """
    Return list of all available professions for frontend
    """
    return [
        {"value": "gp", "label": "General Practitioner"},
        {"value": "nurse", "label": "Nurse"},
        {"value": "midwife", "label": "Midwife"},
        {"value": "lab_tech", "label": "Lab Technologist"},
        {"value": "physiotherapist", "label": "Physiotherapist"},
        {"value": "specialist_nurse", "label": "Specialist Nurse"}
    ]

def get_specialist_types():
    """
    Return list of all available specialist types for nurses
    """
    return [
        {"value": "icu_nurse", "label": "ICU Nurse"},
        {"value": "emergency_nurse", "label": "Emergency Nurse"},
        {"value": "neonatal_nurse", "label": "Neonatal Nurse"},
        {"value": "other", "label": "Other Specialty"}
    ]

# NEW: VALIDATION FUNCTIONS
def validate_email(email: str) -> bool:
    """Validate email format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0.9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def validate_phone_number(phone: str) -> bool:
    """Validate international phone number format - ALL COUNTRIES"""
    # Basic format check: must start with + and have digits
    if not phone.startswith('+'):
        return False
    
    # Remove the + and check if the rest are digits
    digits_only = phone[1:].replace(' ', '')  # Remove any spaces
    
    # Check if we have reasonable number of digits (at least country code + number)
    if len(digits_only) < 7 or not digits_only.isdigit():
        return False
    
    # Check total length (E.164 standard: max 15 digits after +)
    if len(digits_only) > 15:
        return False
    
    # Country code should start with 1-9 (not 0)
    if digits_only[0] == '0':
        return False
    
    return True

def format_phone_number(phone: str) -> str:
    """Format phone number to international format"""
    try:
        parsed_number = phonenumbers.parse(phone, None)
        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        return phone  # Return original if parsing fails



# NEW: RATIONALE PARSING FUNCTION
def parse_rationale_from_question_text(question_data: dict) -> tuple:
    """
    Extract rationale from question text and return cleaned text + rationale
    Handles formats like:
    - "Rationale: explanation text"
    - "✅ Answer: X. Option\nRationale: explanation text" 
    - "Answer: X. Option\nRationale: explanation text"
    """
    text = question_data.get('text', '')
    
    # If rationale is already provided, use it
    if question_data.get('rationale'):
        return text, question_data.get('rationale')
    
    # 🟢 ADD THIS MISSING PART:
    # Look for rationale patterns in the text
    rationale_patterns = [
        r'Rationale:\s*(.+?)(?=\n\s*\d+\.|\n\s*$|$)',
        r'✅ Answer:.*?\nRationale:\s*(.+?)(?=\n\s*\d+\.|\n\s*$|$)',
        r'Answer:.*?\nRationale:\s*(.+?)(?=\n\s*\d+\.|\n\s*$|$)'
    ]
    
    rationale = None
    clean_text = text
    
    for pattern in rationale_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            rationale = match.group(1).strip()
            # Remove the rationale part from the question text
            clean_text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL).strip()
            break
    
    return clean_text, rationale  # This line must be there


# 🟢 ADD THESE HELPER FUNCTIONS AFTER EXISTING UTILITIES



def get_user_gap_profile(user_id: int, db: Session):
    """Get user's knowledge gaps - IMPROVED VERSION"""
    # In a real app, this would analyze the user's exam history
    # For now, let's use a more balanced profile that matches your available topics
    
    # Get available topics from your database
    available_topics = db.query(Question.topic).filter(
        Question.topic.isnot(None)
    ).distinct().all()
    
    available_topics = [t[0] for t in available_topics if t[0]]
    
    print(f"📚 Available topics in database: {available_topics}")
    
    # Create a gap profile that uses actual available topics
    if available_topics:
        # Split available topics into different gap levels
        if len(available_topics) >= 6:
            critical_gaps = available_topics[:2]  # First 2 topics as critical
            moderate_gaps = available_topics[2:4] # Next 2 as moderate
            strong_areas = available_topics[4:6]  # Next 2 as strong
            priority_topics = available_topics[:2] # Same as critical for focus
        else:
            # Fallback if not enough topics
            critical_gaps = ["pharmacology", "clinical_skills"]
            moderate_gaps = ["anatomy", "physiology"]           
            strong_areas = ["patient_care", "medical_ethics"]
            priority_topics = ["drug_interactions", "patient_assessment"]
    else:
        # Fallback profile
        critical_gaps = ["pharmacology", "clinical_skills"]
        moderate_gaps = ["anatomy", "physiology"]           
        strong_areas = ["patient_care", "medical_ethics"]
        priority_topics = ["drug_interactions", "patient_assessment"]
    
    profile = {
        "critical_gaps": critical_gaps,
        "moderate_gaps": moderate_gaps,
        "strong_areas": strong_areas,
        "priority_topics": priority_topics
    }
    
    print(f"🎯 Generated gap profile: {profile}")
    return profile



@app.get("/users/{user_id}/activity")
def get_user_activity(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Users can only see their own activity
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    activities = db.query(UserActivity).filter(UserActivity.user_id == user_id).order_by(UserActivity.timestamp.desc()).all()
    return [
        {
            "activity_type": a.activity_type,
            "timestamp": a.timestamp,
            "details": a.details
        }
        for a in activities
    ]

def select_questions_intelligently(gap_profile, all_questions, total_count):
    """Select questions based on knowledge gaps - FIXED VERSION"""
    print(f"🎯 Starting intelligent selection for {total_count} questions")
    print(f"📊 Gap profile: {gap_profile}")
    print(f"📚 Available questions: {len(all_questions)}")
    
    selected = []
    
    # Strategy: Focus on WEAK areas, not strong ones!
    # 60% critical gaps, 30% moderate gaps, 10% priority topics
    
    # 1. Critical gaps (60%) - user's weakest areas
    critical_count = int(total_count * 0.6)
    critical_questions = [q for q in all_questions if q.topic in gap_profile["critical_gaps"]]
    print(f"🔴 Critical gaps ({gap_profile['critical_gaps']}): {len(critical_questions)} questions available")
    
    if critical_questions:
        import random
        selected_critical = random.sample(critical_questions, min(critical_count, len(critical_questions)))
        selected.extend(selected_critical)
        print(f"✅ Selected {len(selected_critical)} critical gap questions")
    
    # 2. Moderate gaps (30%) - user's moderate weaknesses
    moderate_count = int(total_count * 0.3)
    remaining_questions = [q for q in all_questions if q not in selected]
    moderate_questions = [q for q in remaining_questions if q.topic in gap_profile["moderate_gaps"]]
    print(f"🟡 Moderate gaps ({gap_profile['moderate_gaps']}): {len(moderate_questions)} questions available")
    
    if moderate_questions:
        import random
        selected_moderate = random.sample(moderate_questions, min(moderate_count, len(moderate_questions)))
        selected.extend(selected_moderate)
        print(f"✅ Selected {len(selected_moderate)} moderate gap questions")
    
    # 3. Priority topics (10%) - important topics to focus on
    priority_count = total_count - len(selected)
    remaining_questions = [q for q in all_questions if q not in selected]
    priority_questions = [q for q in remaining_questions if q.topic in gap_profile["priority_topics"]]
    print(f"🔵 Priority topics ({gap_profile['priority_topics']}): {len(priority_questions)} questions available")
    
    if priority_questions and priority_count > 0:
        import random
        selected_priority = random.sample(priority_questions, min(priority_count, len(priority_questions)))
        selected.extend(selected_priority)
        print(f"✅ Selected {len(selected_priority)} priority topic questions")
    
    # 4. Fill remaining slots with random questions (avoid strong areas)
    remaining_count = total_count - len(selected)
    if remaining_count > 0:
        remaining_questions = [q for q in all_questions if q not in selected]
        
        # Avoid strong areas if possible
        non_strong_questions = [q for q in remaining_questions if q.topic not in gap_profile["strong_areas"]]
        
        if non_strong_questions:
            import random
            selected_random = random.sample(non_strong_questions, min(remaining_count, len(non_strong_questions)))
            selected.extend(selected_random)
            print(f"🔄 Selected {len(selected_random)} random questions (avoiding strong areas)")
        elif remaining_questions:
            import random
            selected_random = random.sample(remaining_questions, min(remaining_count, len(remaining_questions)))
            selected.extend(selected_random)
            print(f"🔄 Selected {len(selected_random)} random questions (fallback)")
    
    # Final shuffle and debug info
    import random
    random.shuffle(selected)
    
    # Debug: show what we selected
    selected_topics = {}
    for q in selected:
        topic = q.topic or "unknown"
        selected_topics[topic] = selected_topics.get(topic, 0) + 1
    
    print(f"🎉 Final selection: {len(selected)} questions")
    print(f"📊 Selected topics: {selected_topics}")
    
    return selected



    # Add Auto Lable Function.

def auto_label_questions(db: Session):
    """Automatically add topic labels to existing questions based on content"""
    questions = db.query(Question).filter(Question.topic.is_(None)).all()
    
    if not questions:
        return 0  # No unlabeled questions
    
    print(f"🔍 Found {len(questions)} unlabeled questions to auto-label...")
    
    # Enhanced topic keywords - expanded for better matching
    topic_keywords = {
        "pharmacology": [
            "medication", "drug", "dose", "prescription", "side effect", "contraindication",
            "pharmacology", "antibiotic", "analgesic", "therapeutic", "interaction", "overdose",
            "administration", "dosage", "indication", "adverse", "toxicity", "metabolism",
            "pharmacokinetic", "pharmacodynamic", "therapeutic", "contraindicated", "medication",
            "drug therapy", "prescribed", "antibiotics", "pain medication", "blood pressure medication",
            "insulin", "warfarin", "digoxin", "statins", "ace inhibitor", "beta blocker"
        ],
        "anatomy": [
            "anatomy", "organ", "bone", "muscle", "nerve", "artery", "vein", "heart", "lung",
            "liver", "kidney", "brain", "spinal", "joint", "tissue", "structure", "location",
            "anatomical", "skeletal", "muscular", "nervous", "cardiovascular", "respiratory",
            "gastrointestinal", "endocrine", "reproductive", "urinary", "integumentary",
            "cranial", "thoracic", "abdominal", "pelvic", "extremity", "appendicular"
        ],
        "physiology": [
            "physiology", "function", "metabolism", "hormone", "system", "process", "mechanism",
            "homeostasis", "regulation", "secretion", "absorption", "circulation", "respiration",
            "digestion", "excretion", "reproduction", "neural", "cardiac", "pulmonary", "renal",
            "endocrine", "immune", "pathophysiology", "normal function", "body system"
        ],
        "clinical_skills": [
            "assess", "examine", "procedure", "technique", "skill", "examination", "assessment",
            "diagnostic", "evaluate", "monitor", "observe", "palpate", "auscultate", "inspect",
            "percuss", "measure", "test", "screening", "physical exam", "vital signs", "assessment",
            "nursing intervention", "clinical procedure", "patient examination"
        ],
        "patient_care": [
            "care", "nursing", "patient", "comfort", "hygiene", "support", "education", "teaching",
            "communication", "counseling", "recovery", "rehabilitation", "discharge", "follow-up",
            "nursing care", "patient education", "health teaching", "self-care", "family education",
            "supportive care", "palliative care", "patient safety", "quality of care"
        ],
        "medical_ethics": [
            "ethics", "consent", "confidential", "rights", "legal", "ethical", "privacy", "autonomy",
            "beneficence", "non-maleficence", "justice", "dilemma", "decision", "morality",
            "informed consent", "patient rights", "confidentiality", "ethical principle",
            "advance directive", "power of attorney", "ethical dilemma", "legal issue"
        ],
        "emergency_care": [
            "emergency", "critical", "urgent", "resuscitation", "triage", "crisis", "acute",
            "life-threatening", "cardiac arrest", "shock", "trauma", "emergency department",
            "code blue", "rapid response", "emergency situation", "critical condition",
            "emergency care", "urgent care", "emergency response", "crisis management"
        ],
        "diagnosis": [
            "diagnosis", "diagnose", "test", "result", "interpret", "finding", "symptom", "sign",
            "laboratory", "imaging", "x-ray", "blood test", "diagnostic criteria", "differential",
            "clinical diagnosis", "test result", "lab value", "diagnostic test", "screening test",
            "diagnostic imaging", "laboratory test", "interpretation", "clinical finding"
        ]
    }
    
    updated_count = 0
    for question in questions:
        question_text = question.text.lower()
        
        # Count matches for each topic
        topic_scores = {}
        for topic, keywords in topic_keywords.items():
            score = sum(1 for keyword in keywords if keyword in question_text)
            if score > 0:
                topic_scores[topic] = score
        
        # Assign the topic with highest score (if any match found)
        if topic_scores:
            best_topic = max(topic_scores.items(), key=lambda x: x[1])[0]
            question.topic = best_topic
            
            # Set difficulty based on question characteristics
            text_length = len(question.text)
            word_count = len(question.text.split())
            
            if word_count < 15 or text_length < 100:
                question.difficulty = "basic"
            elif word_count < 30 or text_length < 200:
                question.difficulty = "intermediate"
            else:
                question.difficulty = "advanced"
                
            updated_count += 1
            
            # Print progress for first few questions
            if updated_count <= 5:
                print(f"✅ Labeled: '{question.text[:50]}...' → {best_topic}")
    
    db.commit()
    print(f"🎉 Auto-labeled {updated_count} questions!")
    return updated_count





    
    # Look for rationale patterns in the text
    rationale_patterns = [
        r'Rationale:\s*(.+?)(?=\n\s*\d+\.|\n\s*$|$)',
        r'✅ Answer:.*?\nRationale:\s*(.+?)(?=\n\s*\d+\.|\n\s*$|$)',
        r'Answer:.*?\nRationale:\s*(.+?)(?=\n\s*\d+\.|\n\s*$|$)'
    ]
    
    rationale = None
    clean_text = text
    
    for pattern in rationale_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            rationale = match.group(1).strip()
            # Remove the rationale part from the question text
            clean_text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL).strip()
            break
    
    return clean_text, rationale

# NEW: FUNCTION TO ADD RATIONALE TO EXISTING QUESTIONS
def add_rationale_to_existing_questions(db: Session):
    """Extract rationale from existing questions and update them"""
    print("🔄 Updating existing questions with rationale...")
    
    questions = db.query(Question).all()
    updated_count = 0
    
    for question in questions:
        clean_text, rationale = parse_rationale_from_question_text({
            'text': question.text,
            'rationale': question.rationale
        })
        
        if rationale and (rationale != question.rationale or clean_text != question.text):
            question.text = clean_text
            question.rationale = rationale
            updated_count += 1
            print(f"✅ Updated: {clean_text[:50]}...")
            print(f"   Rationale: {rationale[:50]}...")
    
    db.commit()
    print(f"🎉 Updated {updated_count} questions with rationale!")
    return updated_count

# Initialize database with rationale data
db = SessionLocal()
try:
    add_rationale_to_existing_questions(db)
finally:
    db.close()


# =============================================================================
# NEW PASSWORD RESET ENDPOINT - ADDED HERE
# =============================================================================

@app.post("/reset-password")
async def reset_password(  # FIXED: Changed from 'def' to 'async def'
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Simple password reset endpoint that allows users to reset their own password
    """
    try:
        data = await request.json()
        email = data.get('email')
        new_password = data.get('new_password')
        
        if not email or not new_password:
            return {
                "status": "error",
                "detail": "Email and new password are required"
            }
        
        # Find user by email
        user = get_user_by_email(db, email)
        if not user:
            return {
                "status": "error", 
                "detail": "User not found with this email address"
            }
        
        # Update password with the new one
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        
        # Log the password reset activity
        log_activity(db, user.id, "password_reset", {
            "reset_by": "user",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "status": "success",
            "detail": "Password reset successfully! You can now login with your new password."
        }
            
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "detail": f"Internal server error: {str(e)}"
        }

# ENDPOINTS - UPDATED REGISTRATION WITH VALIDATION AND DISCIPLINE SYSTEM

@app.post("/register")
def register(
    email: str = Body(...),
    full_name: str = Body(...),
    password: str = Body(...),
    phone: Optional[str] = Body(None),
    profession: Optional[str] = Body(None),
    specialist_type: Optional[str] = Body(None),
    db: Session = Depends(get_db)
):
    # Validate email format
    if not validate_email(email):
        raise HTTPException(
            status_code=400, 
            detail="Invalid email format. Please provide a valid email address (e.g., user@example.com)"
        )
    
    # Validate phone number if provided
    if phone and not validate_phone_number(phone):
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number format. Please use international format with country code (e.g., +251911223344)"
        )
    
    # NEW: Validate profession and specialty combination
    if not validate_profession_and_specialty(profession, specialist_type):
        raise HTTPException(
            status_code=400,
            detail="Invalid profession and specialty combination. Specialist type is only allowed for specialist nurses."
        )
    
    # Format phone number if valid
    formatted_phone = format_phone_number(phone) if phone else None
    
    if get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user with pending status
    user = User(
        email=email,
        full_name=full_name,
        phone=formatted_phone,
        profession=profession,
        specialist_type=specialist_type,
        hashed_password=get_password_hash(password),
        status=UserStatus.PENDING
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Calculate the user's discipline_id for logging
    user_discipline_id = get_user_discipline_id(user)
    
    log_activity(db, user.id, "register", {
        "email": email,
        "profession": profession,
        "specialist_type": specialist_type,
        "discipline_id": user_discipline_id,
        "status": UserStatus.PENDING
    })
    
    return {
        "msg": "User registered successfully! Your account is pending admin approval. You will be notified once approved.", 
        "user_id": user.id, 
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "profession": user.profession,
        "specialist_type": user.specialist_type,
        "discipline_id": user_discipline_id,  # NEW: Return calculated discipline_id
        "status": user.status
    }



# =============================================================================
#  ✅ SECURE LOGIN ENDPOINT WITH JWT
# =============================================================================

@app.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = get_user_by_email(db, form_data.username)  # username = email
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is approved
    if user.status != UserStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending approval. Please wait for admin approval."
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"user_id": user.id}, expires_delta=access_token_expires
    )
    
    # Log the login activity
    log_activity(db, user.id, "login", {})
    
    return {

        "access_token": access_token,
    "token_type": "bearer",
    "user_id": user.id,
    "full_name": user.full_name,
    "profession": user.profession,
    "email": user.email,
    "premium_features": user.premium_features if hasattr(user, 'premium_features') and user.premium_features is not None else {
        "ai_simulation": False,
        "procedure_trainer": False,
        "ai_job_match": False,
        "usmle": False
    }
}

@app.put("/admin/users/{user_id}/features")
async def update_user_features(
    user_id: int,
    request: dict,
    db: Session = Depends(get_db)
):
    new_features = request.get("premium_features", {})
    
    # Use direct SQL with text()
    db.execute(
        text("UPDATE users SET premium_features = :features WHERE id = :user_id"),
        {"features": json.dumps(new_features), "user_id": user_id}
    )
    db.commit()
    
    return {
        "message": "User features updated",
        "user_id": user_id,
        "premium_features": new_features
    }








# NEW: PROFESSION INFORMATION ENDPOINTS
@app.get("/professions")
def get_professions():
    """Get all available professions for registration"""
    return get_available_professions()

@app.get("/specialist-types")
def get_specialist_types_endpoint():
    """Get all available specialist types for nurses"""
    return get_specialist_types()



@app.get("/users/{user_id}/activity")
def get_user_activity(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Users can only see their own activity
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    activities = db.query(UserActivity).filter(UserActivity.user_id == user_id).order_by(UserActivity.timestamp.desc()).all()
    return [
        {
            "activity_type": a.activity_type,
            "timestamp": a.timestamp,
            "details": a.details
        }
        for a in activities
    ]





# =============================================================================
# QUIZ ENDPOINTS - START
# =============================================================================



@app.get("/debug/smart-quiz-test")
def debug_smart_quiz_test(db: Session = Depends(get_db)):
    """Test Smart Quiz generation with debug info"""
    try:
        # Simulate a user request
        from collections import Counter
        
        # Get all quiz questions
        all_questions = db.query(Question).join(Exam).filter(
            Exam.source == "plural",
            Question.topic.isnot(None)
        ).all()
        
        print(f"🔍 Total quiz questions: {len(all_questions)}")
        
        # Show topic distribution
        topic_counts = Counter([q.topic for q in all_questions if q.topic])
        print(f"📊 Topic distribution: {dict(topic_counts)}")
        
        # Test gap profile
        test_profile = {
            "critical_gaps": ["pharmacology", "clinical_skills"],
            "moderate_gaps": ["anatomy", "physiology"],           
            "strong_areas": ["patient_care", "medical_ethics"],
            "priority_topics": ["drug_interactions", "patient_assessment"]
        }
        
        # Test selection
        selected = select_questions_intelligently(test_profile, all_questions, 10)
        
        return {
            "total_quiz_questions": len(all_questions),
            "topic_distribution": dict(topic_counts),
            "test_profile": test_profile,
            "selected_count": len(selected),
            "selected_topics": dict(Counter([q.topic for q in selected if q.topic])),
            "ready_for_smart_quiz": len(all_questions) >= 10
        }
        
    except Exception as e:
        return {"error": str(e)}


@app.post("/quiz/create")
def create_quiz(
    title: str = Body(...),
    discipline: str = Body(...),
    questions: List[dict] = Body(...),
    #current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new quiz with properly labeled questions"""
    try:
        exam_id = f"quiz_{str(uuid.uuid4())[:8]}"
        
        # Create quiz exam
        quiz_exam = Exam(
            id=exam_id,
            title=title,
            discipline_id=discipline,
            time_limit=45,
            source="quiz",  # Special source for quizzes
            is_released=True
        )
        db.add(quiz_exam)
        db.commit()
        
        # Create quiz questions with proper labeling
        created_count = 0
        for i, q_data in enumerate(questions):
            question = Question(
                id=f"{exam_id}_q{i+1}",
                exam_id=exam_id,
                text=q_data.get("text", ""),
                options=q_data.get("options", []),
                correct_idx=q_data.get("correct_idx", 0),
                rationale=q_data.get("rationale", ""),
                topic=q_data.get("topic", "general"),  # Required for Smart Quiz
                subtopic=q_data.get("subtopic", ""),
                difficulty=q_data.get("difficulty", "intermediate")
            )
            db.add(question)
            created_count += 1
        
        db.commit()
                      
        return {
            "success": True,
            "quiz_id": exam_id,
            "title": title,
            "questions_created": created_count,
            "message": f"Quiz '{title}' created successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create quiz: {str(e)}")



@app.get("/quiz/list")
def list_quizzes(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all available quizzes"""
    quizzes = db.query(Exam).filter(Exam.source == "quiz").all()
    
    return [
        {
            "id": quiz.id,
            "title": quiz.title,
            "discipline": quiz.discipline_id,
            "question_count": db.query(Question).filter(Question.exam_id == quiz.id).count(),
            "created_at": quiz.release_date
        }
        for quiz in quizzes
    ]


@app.get("/quiz/{quiz_id}")
def get_quiz(
    quiz_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific quiz with its questions"""
    quiz = db.query(Exam).filter(Exam.id == quiz_id, Exam.source == "quiz").first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    questions = db.query(Question).filter(Question.exam_id == quiz_id).all()
    
    return {
        "id": quiz.id,
        "title": quiz.title,
        "discipline": quiz.discipline_id,
        "time_limit": quiz.time_limit,
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "options": q.options,
                "correct_idx": q.correct_idx,
                "rationale": q.rationale,
                "topic": q.topic,
                "subtopic": q.subtopic,
                "difficulty": q.difficulty
            }
            for q in questions
        ]
    }



@app.get("/quiz/intelligent/{exam_id}")
def get_intelligent_quiz(
    exam_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a Smart Quiz exam (intelligent source)"""
    exam = db.query(Exam).filter(Exam.id == exam_id, Exam.source == "intelligent").first()
    if not exam:
        raise HTTPException(status_code=404, detail="Smart Quiz not found")
    
    questions = db.query(Question).filter(Question.exam_id == exam_id).all()
    
    return {
        "id": exam.id,
        "title": exam.title,
        "discipline": exam.discipline_id,
        "time_limit": exam.time_limit,
        "questions": [
            {
                "text": q.text,
                "options": q.options,
                "correct_idx": q.correct_idx,
                "rationale": q.rationale,
                "topic": getattr(q, 'topic', 'general'),
                "difficulty": getattr(q, 'difficulty', 'intermediate')
            }
            for q in questions
        ]
    }



@app.post("/quiz/intelligent/generate")
def generate_intelligent_quiz(
    request: IntelligentExamRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate a Smart Quiz from QUIZ questions only"""
    try:
        # Get user's actual discipline
        user_discipline = get_user_discipline_id(current_user)
        print(f"🎯 Generating Smart Quiz for {user_discipline} user: {current_user.email}")
        
        # Get user's knowledge gaps
        gap_profile = get_user_gap_profile(current_user.id, db)
        
        # 🟢 FIXED: Get ONLY QUIZ questions for user's discipline
        print(f"🔍 Querying for QUIZ questions only (source='quiz')...")
        all_quiz_questions = db.query(Question).join(Exam).filter(
            Exam.source == "quiz",  # ✅ ONLY quiz source
            Exam.discipline_id == user_discipline,
            Question.topic.isnot(None),
            Question.topic != ''  # ✅ Ensure topic is not empty
        ).all()

        print(f"✅ Found {len(all_quiz_questions)} QUIZ questions with topics")
        
        # 🟢 DEBUG: Verify we're only getting quiz questions
        if all_quiz_questions:
            # Check exam sources of the found questions
            exam_sources = set()
            for q in all_quiz_questions:
                exam = db.query(Exam).filter(Exam.id == q.exam_id).first()
                if exam:
                    exam_sources.add(exam.source)
            
            print(f"📊 Exam sources in results: {exam_sources}")
            
            # Show topics distribution
            topics_count = {}
            for q in all_quiz_questions:
                topics_count[q.topic] = topics_count.get(q.topic, 0) + 1
            print(f"📊 Topics distribution: {topics_count}")
        
        if not all_quiz_questions:
            raise HTTPException(status_code=404, detail=f"No quiz questions available for {user_discipline}")

        # Intelligent question selection
        print(f"🎯 Starting intelligent selection for {request.question_count or 15} questions")
        selected_questions = select_questions_intelligently(
            gap_profile, 
            all_quiz_questions, 
            request.question_count or 15
        )
        print(f"✅ Selected {len(selected_questions)} questions")

        # Create the Smart Quiz
        exam_id = str(uuid.uuid4())
        print(f"📝 Creating Smart Quiz: {exam_id}")

        intelligent_exam = Exam(
            id=exam_id,
            title=f"Smart Quiz - {user_discipline} - {datetime.now().strftime('%m/%d')}",
            discipline_id=user_discipline,
            time_limit=45,
            source="intelligent",
            is_released=True
        )
        db.add(intelligent_exam)
        db.commit()
        print("✅ Smart Quiz exam created in database")

        # 🟢 Insert the selected questions into the database
        created_count = 0
        print(f"💾 Saving {len(selected_questions)} questions to Smart Quiz...")
        for i, question in enumerate(selected_questions):
            new_question = Question(
                id=f"{exam_id}_q{i+1}",
                exam_id=exam_id,
                text=question.text,
                options=question.options,
                correct_idx=question.correct_idx,
                rationale=question.rationale,
                topic=question.topic,
                subtopic=getattr(question, 'subtopic', ''),
                difficulty=getattr(question, 'difficulty', 'intermediate')
            )
            db.add(new_question)
            created_count += 1

        db.commit()
        print(f"✅ Saved {created_count} questions to Smart Quiz {exam_id}")

        return {
            "exam_id": exam_id,
            "title": intelligent_exam.title,
            "discipline": user_discipline,
            "question_count": len(selected_questions),
            "focus_areas": request.focus_areas or [],
            "questions": [
                {
                    "text": q.text,
                    "options": q.options,
                    "correct_idx": q.correct_idx,
                    "rationale": q.rationale,
                    "topic": q.topic,
                    "difficulty": q.difficulty
                }
                for q in selected_questions
            ]
        }
        
    except Exception as e:
        print(f"❌ Error generating intelligent quiz: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate Smart Quiz: {str(e)}")



# =============================================================================
# AI-HYBRID QUIZ ENDPOINT (5% AI / 95% Curated)
# =============================================================================

# Add these imports at the top of your file
import os
from typing import Optional, Dict, Any, List
import openai
import asyncio
from datetime import datetime, timedelta




# ====================== AI MODELS & CONFIG ======================

class AIQuestionConfig:
    """Configuration for AI question generation"""
    model: str = "gpt-4o-mini"  # Cost-effective
    max_tokens: int = 800
    temperature: float = 0.7
    max_retries: int = 2

class AIQuestionRequest:
    """Request structure for AI question generation"""
    topic: str
    user_profession: str
    difficulty: str = "intermediate"
    common_errors: List[str] = []
    question_context: Optional[str] = None

class AIQuestionResponse:
    """Response structure for AI-generated question"""
    text: str
    options: List[str]
    correct_idx: int
    rationale: str
    topic: str
    difficulty: str
    is_ai_generated: bool = True

# ====================== AI QUESTION ENGINE ======================

class AIQuestionEngine:
    """Handles AI question generation with medical focus"""
    
    def __init__(self, config: AIQuestionConfig = None):
        self.config = config or AIQuestionConfig()
        self.daily_ai_count = 0  # Track for 5% limit
        self.daily_reset_time = datetime.now().date()
    
    def _reset_daily_count(self):
        """Reset daily counter if new day"""
        today = datetime.now().date()
        if today != self.daily_reset_time:
            self.daily_ai_count = 0
            self.daily_reset_time = today
    
    def _can_generate_ai(self, total_questions: int) -> bool:
        """Check if we're within 5% AI limit"""
        self._reset_daily_count()
        
        # Allow at least 1 AI question per quiz, but respect 5% limit
        ai_limit = max(1, int(total_questions * 0.05))
        
        # Simple daily limit to prevent abuse
        daily_limit = 100  # Max 100 AI questions per day
        
        return (self.daily_ai_count < daily_limit)
    
    async def generate_medical_question(
        self,
        topic: str,
        user_profession: str,
        difficulty: str = "intermediate",
        common_errors: List[str] = None,
        question_context: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate ONE AI question based on specific needs"""
        
        try:
            # Build medical-specific prompt
            prompt = self._build_medical_question_prompt(
                topic=topic,
                profession=user_profession,
                difficulty=difficulty,
                common_errors=common_errors or [],
                context=question_context
            )
            
            # Call OpenAI with timeout
           # First, make sure you have the client initialized earlier
# Add at the top of your file or class:
# from openai import OpenAI
# client = OpenAI(api_key=config.OPENAI_API_KEY)

                    # Call OpenAI with timeout
            try:
                response = await asyncio.wait_for(
                    openai_client.chat.completions.create(
                        model=self.config.model,
                        messages=[
                            {
                                "role": "system", 
                                "content": """You are a medical education expert. Generate high-quality multiple-choice questions for healthcare professionals.
                                Follow these rules:
                                1. Questions must be medically accurate and evidence-based
                                2. All options should be plausible but only one correct
                                3. Include detailed rationales explaining why the answer is correct and others are wrong
                                4. Use clear, professional medical language
                                5. Avoid ambiguous wording"""
                            },
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=self.config.max_tokens,
                        temperature=self.config.temperature
                    ),
                    timeout=10.0
                )
            except Exception as e:
                print(f"❌ OpenAI API error: {e}")
                return None
            
            ai_text = response.choices[0].message.content
            
            # Parse the response
            question_data = self._parse_ai_response(ai_text)
            if question_data:
                self.daily_ai_count += 1
                return question_data
            
            return None
            
        except asyncio.TimeoutError:
            print("⚠️ AI generation timeout")
            return None
        except Exception as e:
            print(f"⚠️ AI generation error: {e}")
            return None
    
    def _build_medical_question_prompt(
        self,
        topic: str,
        profession: str,
        difficulty: str,
        common_errors: List[str],
        context: Optional[str] = None
    ) -> str:
        """Build specific prompt for medical questions"""
        
        base_prompt = f"""
        Generate ONE multiple-choice question for {profession} education.
        
        REQUIREMENTS:
        - Topic: {topic}
        - Difficulty: {difficulty}
        - Format: Multiple choice with 4 options (A, B, C, D)
        - Include detailed rationale explaining both correct and incorrect answers
        
        SPECIFIC INSTRUCTIONS:
        1. Question should test practical knowledge relevant to {profession}
        2. Address these common misconceptions: {', '.join(common_errors[:3]) if common_errors else 'general understanding'}
        3. Make all options plausible but only one clearly correct
        4. Rationale should explain why correct answer is right AND why others are wrong
        
        CONTEXT FROM SIMILAR QUESTIONS:
        {context if context else 'No specific context provided.'}
        
        OUTPUT FORMAT (EXACTLY like this):
        QUESTION: [question text]
        OPTIONS:
        A) [option 1]
        B) [option 2]
        C) [option 3]
        D) [option 4]
        CORRECT: [A/B/C/D]
        RATIONALE: [detailed explanation]
        TOPIC: {topic}
        DIFFICULTY: {difficulty}
        """
        
        return base_prompt
    
    def _parse_ai_response(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse AI response into structured question data"""
        try:
            # Extract question text
            question_match = re.search(r'QUESTION:\s*(.+?)(?=\nOPTIONS:|$)', text, re.DOTALL)
            if not question_match:
                return None
            
            question_text = question_match.group(1).strip()
            
            # Extract options
            options_match = re.findall(r'[A-D]\)\s*(.+?)(?=\n[A-D]\)|\nCORRECT:|$)', text, re.DOTALL)
            if len(options_match) < 4:
                # Try alternative pattern
                options_match = re.findall(r'[A-D]\.\s*(.+?)(?=\n[A-D]\.|\nCORRECT:|$)', text, re.DOTALL)
            
            if len(options_match) < 4:
                return None
            
            options = [opt.strip() for opt in options_match[:4]]
            
            # Extract correct answer
            correct_match = re.search(r'CORRECT:\s*([A-D])', text, re.IGNORECASE)
            if not correct_match:
                return None
            
            correct_letter = correct_match.group(1).upper()
            correct_idx = ord(correct_letter) - ord('A')
            
            # Extract rationale
            rationale_match = re.search(r'RATIONALE:\s*(.+?)(?=\nTOPIC:|$)', text, re.DOTALL)
            rationale = rationale_match.group(1).strip() if rationale_match else "See medical guidelines."
            
            # Extract topic and difficulty (optional)
            topic_match = re.search(r'TOPIC:\s*(.+)', text, re.IGNORECASE)
            difficulty_match = re.search(r'DIFFICULTY:\s*(.+)', text, re.IGNORECASE)
            
            return {
                "text": question_text,
                "options": options,
                "correct_idx": correct_idx,
                "rationale": rationale,
                "topic": topic_match.group(1).strip() if topic_match else "general",
                "difficulty": difficulty_match.group(1).strip() if difficulty_match else "intermediate",
                "is_ai_generated": True
            }
            
        except Exception as e:
            print(f"⚠️ Failed to parse AI response: {e}")
            return None
    
    async def enhance_explanation(
        self,
        base_rationale: str,
        topic: str,
        user_profession: str
    ) -> str:
        """Enhance existing explanation with AI"""
        try:
            prompt = f"""
            Improve this medical explanation for a {user_profession}:
            
            Original explanation: {base_rationale}
            
            Topic: {topic}
            
            Make it:
            1. More detailed and clinically relevant
            2. Include practical implications for {user_profession}
            3. Keep the same technical level
            4. Add key learning points
            
            Return ONLY the enhanced explanation (no markdown, no labels).
            """
            
            response = await asyncio.wait_for(
    # ✅ NEW SYNTAX:
    openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a medical educator enhancing explanations."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300,
        temperature=0.3
    ),
    timeout=5.0
)
            
            enhanced = response.choices[0].message.content.strip()
            return enhanced if enhanced and len(enhanced) > 50 else base_rationale
            
        except Exception:
            return base_rationale  # Fallback to original

# ====================== AI INTEGRATION SERVICE ======================

class AIIntegrationService:
    """Orchestrates AI integration with existing quiz system"""
    
    def __init__(self):
        self.ai_engine = AIQuestionEngine()
        self.ai_usage_log = {}
    
    def identify_ai_candidate(
        self,
        gap_profile: Dict,
        curated_questions: List[Question],
        user_profession: str
    ) -> Optional[Dict]:
        """Identify which topic needs AI question"""
        
        if not gap_profile or not curated_questions:
            return None
        
        # Find the topic with worst performance (critical gap)
        critical_gaps = gap_profile.get("critical_gaps", [])
        if not critical_gaps:
            return None
        
        # Get most frequent critical gap
        gap_topic = critical_gaps[0] if critical_gaps else None
        if not gap_topic:
            return None
        
        # Check if we already have curated questions on this topic
        curated_on_topic = [q for q in curated_questions if q.topic == gap_topic]
        
        # If we have few curated questions on this topic, it's a good candidate for AI
        if len(curated_on_topic) <= 2:  # Few existing questions
            return {
                "topic": gap_topic,
                "reason": "Few existing questions on this critical gap topic",
                "common_errors": gap_profile.get("common_errors", {}).get(gap_topic, []),
                "user_profession": user_profession
            }
        
        return None
    
    async def generate_ai_question_for_gap(
        self,
        gap_info: Dict,
        context_questions: List[Question] = None
    ) -> Optional[Dict]:
        """Generate AI question for identified gap"""
        
        # Build context from similar questions
        context = None
        if context_questions:
            context_texts = [q.text[:200] for q in context_questions[:2]]  # First 200 chars of 2 questions
            context = "Similar existing questions:\n" + "\n".join(context_texts)
        
        # Generate AI question
        ai_question = await self.ai_engine.generate_medical_question(
            topic=gap_info["topic"],
            user_profession=gap_info["user_profession"],
            difficulty="intermediate",
            common_errors=gap_info.get("common_errors", []),
            question_context=context
        )
        
        return ai_question
    
    async def enhance_question_explanations(
        self,
        questions: List[Question],
        user_profession: str
    ) -> List[Question]:
        """Enhance explanations for selected questions"""
        
        enhanced_questions = []
        
        for question in questions:
            # Only enhance if rationale exists and is not too long
            if question.rationale and len(question.rationale) < 500:
                try:
                    enhanced_rationale = await self.ai_engine.enhance_explanation(
                        base_rationale=question.rationale,
                        topic=question.topic or "general",
                        user_profession=user_profession
                    )
                    
                    # Create enhanced question (don't modify original)
                    enhanced_question = Question(
                        id=question.id,
                        exam_id=question.exam_id,
                        text=question.text,
                        options=question.options,
                        correct_idx=question.correct_idx,
                        rationale=enhanced_rationale,
                        topic=question.topic,
                        subtopic=question.subtopic,
                        difficulty=question.difficulty
                    )
                    enhanced_questions.append(enhanced_question)
                except Exception:
                    enhanced_questions.append(question)  # Keep original
            else:
                enhanced_questions.append(question)  # Keep original
        
        return enhanced_questions

# ====================== MAIN AI-HYBRID ENDPOINT ======================

@app.post("/quiz/ai-hybrid/generate")
async def generate_ai_hybrid_quiz(
    request: IntelligentExamRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Generate Smart Quiz with 5% AI-generated questions and enhanced explanations
    Returns quiz identical in format to original, but with AI enhancements
    """
    try:
        print(f"🎯 Generating AI-Hybrid Quiz for {current_user.email}")
        
        # Get user's actual discipline
        user_discipline = get_user_discipline_id(current_user)
        
        # Get user's knowledge gaps
        gap_profile = get_user_gap_profile(current_user.id, db)
        print(f"📊 User gap profile: {gap_profile}")
        
        # Get ONLY QUIZ questions for user's discipline (95% of content)
        print(f"🔍 Querying for QUIZ questions only (source='quiz')...")
        all_quiz_questions = db.query(Question).join(Exam).filter(
            Exam.source == "quiz",
            Exam.discipline_id == user_discipline,
            Question.topic.isnot(None),
            Question.topic != ''
        ).all()
        
        print(f"✅ Found {len(all_quiz_questions)} QUIZ questions with topics")
        
        if not all_quiz_questions:
            raise HTTPException(
                status_code=404, 
                detail=f"No quiz questions available for {user_discipline}"
            )
        
        # Calculate question counts
        total_questions = request.question_count or 15
        curated_count = max(1, int(total_questions * 0.95))  # 95% curated
        ai_count = total_questions - curated_count  # 5% AI
        
        print(f"📐 Target: {total_questions} total ({curated_count} curated, {ai_count} AI)")
        
        # Select curated questions (using your existing intelligent selection)
        curated_questions = select_questions_intelligently(
            gap_profile, 
            all_quiz_questions, 
            curated_count
        )
        print(f"✅ Selected {len(curated_questions)} curated questions")
        
        # Initialize AI service
        ai_service = AIIntegrationService()
        
        # Generate AI questions if needed (5%)
        ai_questions = []
        if ai_count > 0 and len(curated_questions) > 0:
            print(f"🤖 Attempting to generate {ai_count} AI questions...")
            
            # Identify which topic needs AI question
            gap_info = ai_service.identify_ai_candidate(
                gap_profile=gap_profile,
                curated_questions=curated_questions,
                user_profession=user_discipline
            )
            
            if gap_info:
                print(f"🎯 AI candidate topic: {gap_info['topic']}")
                
                # Get similar questions for context
                similar_questions = [q for q in curated_questions if q.topic == gap_info["topic"]][:2]
                
                # Generate AI question
                ai_question_data = await ai_service.generate_ai_question_for_gap(
                    gap_info=gap_info,
                    context_questions=similar_questions
                )
                
                if ai_question_data:
                    print(f"✅ Generated AI question on {gap_info['topic']}")
                    ai_questions.append(ai_question_data)
                else:
                    print("⚠️ AI generation failed, using extra curated question")
            else:
                print("ℹ️ No suitable AI candidate found, using curated only")
        
        # Combine questions (AI questions first, then curated)
        all_questions = ai_questions + curated_questions[:total_questions - len(ai_questions)]
        
        # Ensure we have exactly total_questions
        if len(all_questions) < total_questions:
            # Add more curated questions if needed
            remaining = total_questions - len(all_questions)
            extra_questions = [q for q in all_quiz_questions if q not in all_questions][:remaining]
            all_questions.extend(extra_questions)
        
        print(f"🎉 Final: {len(all_questions)} questions ({len(ai_questions)} AI)")
        
        # Enhance explanations with AI (optional - can be disabled if too slow)
        enhanced_questions = all_questions  # Default to no enhancement
        
        # Uncomment to enable AI-enhanced explanations:
        # print("🧠 Enhancing explanations with AI...")
        # enhanced_questions = await ai_service.enhance_question_explanations(
        #     questions=all_questions,
        #     user_profession=user_discipline
        # )
        # print("✅ Explanations enhanced")
        
        # Create the Smart Quiz in database (identical to your existing code)
        exam_id = str(uuid.uuid4())
        print(f"📝 Creating AI-Hybrid Quiz: {exam_id}")
        
        intelligent_exam = Exam(
            id=exam_id,
            title=f"AI-Enhanced Quiz - {user_discipline} - {datetime.now().strftime('%m/%d')}",
            discipline_id=user_discipline,
            time_limit=45,
            source="intelligent",
            is_released=True
        )
        db.add(intelligent_exam)
        db.commit()
        print("✅ AI-Hybrid Quiz exam created in database")
        
        # Insert questions into database
        created_count = 0
        print(f"💾 Saving {len(enhanced_questions)} questions to quiz...")
        
        for i, question in enumerate(enhanced_questions):
            # Handle both Question objects and AI dicts
            if isinstance(question, dict):  # AI-generated question
                new_question = Question(
                    id=f"{exam_id}_q{i+1}",
                    exam_id=exam_id,
                    text=question["text"],
                    options=question["options"],
                    correct_idx=question["correct_idx"],
                    rationale=question["rationale"],
                    topic=question["topic"],
                    difficulty=question["difficulty"]
                )
            else:  # Curated Question object
                new_question = Question(
                    id=f"{exam_id}_q{i+1}",
                    exam_id=exam_id,
                    text=question.text,
                    options=question.options,
                    correct_idx=question.correct_idx,
                    rationale=question.rationale,
                    topic=question.topic,
                    subtopic=getattr(question, 'subtopic', ''),
                    difficulty=getattr(question, 'difficulty', 'intermediate')
                )
            
            db.add(new_question)
            created_count += 1
        
        db.commit()
        print(f"✅ Saved {created_count} questions to quiz {exam_id}")
        
        # Prepare response (identical format to original endpoint)
        response_questions = []
        for question in enhanced_questions:
            if isinstance(question, dict):
                response_questions.append({
                    "text": question["text"],
                    "options": question["options"],
                    "correct_idx": question["correct_idx"],
                    "rationale": question["rationale"],
                    "topic": question["topic"],
                    "difficulty": question["difficulty"]
                })
            else:
                response_questions.append({
                    "text": question.text,
                    "options": question.options,
                    "correct_idx": question.correct_idx,
                    "rationale": question.rationale,
                    "topic": question.topic,
                    "difficulty": question.difficulty
                })
        
        return {
            "exam_id": exam_id,
            "title": intelligent_exam.title,
            "discipline": user_discipline,
            "question_count": len(response_questions),
            "focus_areas": request.focus_areas or [],
            "ai_enhanced": True,  # Only difference - indicates AI was used
            "questions": response_questions
        }
        
    except Exception as e:
        print(f"❌ Error generating AI-hybrid quiz: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Fallback to original intelligent quiz if AI fails
        print("🔄 Falling back to regular intelligent quiz...")
        
        # Reuse your existing endpoint logic
        from fastapi import HTTPException
        
        # Call your original function (simplified fallback)
        # In production, you might want to redirect to the original endpoint
        raise HTTPException(
            status_code=500, 
            detail=f"AI enhancement failed: {str(e)}. Please try the regular Smart Quiz."
        )





@app.get("/quiz/ai-hybrid/{exam_id}")
def get_ai_hybrid_quiz(
    exam_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get an AI-hybrid quiz"""
    exam = db.query(Exam).filter(
        Exam.id == exam_id,
        Exam.source == "intelligent"  # or "ai-hybrid" if you changed it
    ).first()
    
    if not exam:
        raise HTTPException(status_code=404, detail="AI-Hybrid Quiz not found")
    
    questions = db.query(Question).filter(Question.exam_id == exam_id).all()
    
    return {
        "id": exam.id,
        "title": exam.title,
        "discipline_id": exam.discipline_id,
        "time_limit": exam.time_limit,
        "questions": [
            {
                "text": q.text,
                "options": q.options,
                "correct_idx": q.correct_idx,
                "rationale": q.rationale,
                "topic": q.topic,
                "difficulty": q.difficulty
            }
            for q in questions
        ]
    }


# ====================== ADMIN AI MONITORING ======================

@app.get("/admin/ai-usage")
def get_ai_usage_stats(db: Session = Depends(get_db)):
    """Admin endpoint to monitor AI usage"""
    # Count exams with AI source (you might want to add an AI flag to exams)
    ai_exams = db.query(Exam).filter(
        Exam.source == "intelligent",
        Exam.title.like("%AI-Enhanced%")
    ).count()
    
    total_exams = db.query(Exam).filter(Exam.source == "intelligent").count()
    
    # Count questions (would need to track AI questions separately)
    total_questions = db.query(Question).join(Exam).filter(
        Exam.source == "intelligent"
    ).count()
    
    return {
        "ai_enhanced_exams": ai_exams,
        "total_smart_quizzes": total_exams,
        "ai_adoption_rate": round((ai_exams / total_exams * 100), 2) if total_exams > 0 else 0,
        "total_questions_generated": total_questions,
        "status": "AI integration active" if openai_client else "AI not configured"
    }

# ====================== UTILITY FUNCTIONS ======================

# ====================== UTILITY FUNCTIONS ======================

def validate_openai_key():
    """Validate OpenAI API key on startup"""
    if not openai_client:
        # If client not initialized, AI features are disabled
        print("⚠️ OpenAI not configured - AI features disabled")
        print("⚠️ WARNING: OpenAI API key not configured")
        print("⚠️ AI features will be disabled")
        return False
    
    try:
        # Simple validation by checking model list
        models = openai_client.models.list()
        print(f"✅ OpenAI API key validated, {len(models.data)} models available")
        return True
    except Exception as e:
        print(f"❌ OpenAI API key validation failed: {e}")
        return False

# Call validation on import
validate_openai_key()



# =============================================================================
# QUIZ ENDPOINTS - END
# =============================================================================



# =============================================================================
# EXAM ENDPOINTS - START
# =============================================================================


@app.post("/exams/submit")
def submit_exam_results(
    exam_data: dict = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Enhanced exam submission endpoint - stores detailed answers in activity log"""
    try:
        # Get exam details
        exam = db.query(Exam).filter(Exam.id == exam_data.get("exam_id")).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        # Extract data
        score = exam_data.get("score", 0)
        total_questions = exam_data.get("total_questions", 0)
        
        # NEW: Get user answers if provided
        user_answers = exam_data.get("user_answers", {})
        
        # Store in user_activity WITH detailed answers
        activity = log_activity(db, current_user.id, "exam_completed", {
            "exam_id": exam_data.get("exam_id"),
            "exam_title": exam.title,
            "score": score,
            "total_questions": total_questions,
            "percentage": score,
            "passed": score >= 70,
            "timestamp": datetime.utcnow().isoformat(),
            # NEW: Add user answers to activity data
            "user_answers": user_answers  # Store whatever is sent
        })
        
        return {
            "message": "Exam results saved successfully",
            "activity_id": activity.id,
            "score": score,
            "answers_received": len(user_answers)  # NEW: Just for debugging
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving results: {str(e)}")





@app.post("/exams")
def create_exam_plural(
    exam_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Create a new plural exam (formal exams)"""
    try:
        exam_id = exam_data.get("id")
        title = exam_data.get("title")
        discipline_id = exam_data.get("discipline_id")
        time_limit = exam_data.get("time_limit", 50)
        source = "plural"  # Always plural for this endpoint
        questions_data = exam_data.get("questions", [])
        
        # Check if exam already exists
        existing_exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if existing_exam:
            return {"msg": f"Exam {exam_id} already exists"}
        
        # Create exam
        exam = Exam(
            id=exam_id,
            title=title,
            discipline_id=discipline_id,
            time_limit=time_limit,
            source=source,
            is_released=False  # Don't auto-release formal exams
        )
        db.add(exam)
        db.commit()
        
        # Create questions
        for q_data in questions_data:
            question = Question(
                id=q_data.get("id", str(uuid.uuid4())),
                exam_id=exam_id,
                text=q_data.get("text", ""),
                options=q_data.get("options", []),
                correct_idx=q_data.get("correct_idx", -1),
                rationale=q_data.get("rationale")
            )
            db.add(question)
        
        db.commit()
        
        return {
            "msg": "Plural exam created successfully",
            "exam_id": exam_id,
            "questions_count": len(questions_data)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating exam: {str(e)}")





@app.get("/exams")
def list_exams_plural(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user_discipline_id = get_user_discipline_id(current_user)
    
    exams = db.query(Exam).filter(
        Exam.source == "plural",
        Exam.discipline_id == user_discipline_id,  # Use dynamic discipline
        Exam.is_released == True
    ).all()
    
    return [
        {
            "id": exam.id,
            "title": exam.title,
            "discipline_id": exam.discipline_id,
            "time_limit": exam.time_limit,
            "source": exam.source
        }
        for exam in exams
    ]

@app.get("/exams/{exam_id}")
def get_exam_with_questions_plural(
    exam_id: str, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user_discipline_id = get_user_discipline_id(current_user)
    
    exam = db.query(Exam).filter(
        Exam.id == exam_id, 
        Exam.source == "plural",
        Exam.discipline_id == user_discipline_id,  # Use dynamic discipline
        Exam.is_released == True
    ).first()
    
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found or access denied")
    
    questions = db.query(Question).filter(Question.exam_id == exam_id).all()
    return {
        "id": exam.id,
        "title": exam.title,
        "discipline_id": exam.discipline_id,
        "time_limit": exam.time_limit,
        "source": exam.source,
        "questions": [
            {
                "text": q.text,
                "options": q.options,
                "correct_idx": q.correct_idx,
                "rationale": q.rationale
            } for q in questions
        ]
    }




# DELETE SPECIfic Exam

@app.delete("/admin/exams/{exam_id}")
def delete_singular_exam(
    exam_id: str,
    db: Session = Depends(get_db)
):
    """Delete a study note (singular exam)"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="exam not found")
    
    db.delete(exam)
    db.commit()
    
    return {"msg": f"exam '{exam.title}' deleted successfully"}




@app.delete("/admin/exams/discipline/{discipline}")
def delete_study_notes_by_discipline(
    discipline: str,
    db: Session = Depends(get_db)
):
    """Delete all exam (plural) for a specific discipline"""
    # Find all singular exams (study notes) for this discipline
    exams = db.query(Exam).filter(
        Exam.discipline_id == discipline,
        Exam.source == "plural"
    ).all()
    
    if not exams:
        raise HTTPException(status_code=404, detail=f"No exam found for discipline: {discipline}")
    
    # SIMPLE DELETE - just like the working function
    deleted_count = db.query(Exam).filter(
        Exam.discipline_id == discipline,
        Exam.source == "plural"
    ).delete()
    
    db.commit()
    
    return {
        "msg": f"Deleted {deleted_count} exam for discipline: {discipline}",
        "deleted_count": deleted_count,
        "discipline": discipline
    }

# =============================================================================
# EXAM ENDPOINTS - END
# =============================================================================

# =============================================================================
# STUDY NOTES ENDPOINTS START
# =============================================================================

# dont forget note end point has exam path

@app.get("/exam")
def list_exam_singular(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Use current_user instead of user_id parameter
    user_discipline_id = get_user_discipline_id(current_user)
    
    exams = db.query(Exam).filter(
        Exam.source == "singular",
        Exam.discipline_id == user_discipline_id  # Use dynamic discipline
    ).all()
    
    return [
        {
            "id": exam.id,
            "title": exam.title,
            "discipline_id": exam.discipline_id,
            "time_limit": exam.time_limit,
            "source": exam.source
        }
        for exam in exams
    ]


@app.get("/exam/{exam_id}")
def get_exam_with_questions_singular(
    exam_id: str, 
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user_discipline_id = get_user_discipline_id(current_user)
    
    exam = db.query(Exam).filter(
        Exam.id == exam_id, 
        Exam.source == "singular",
        Exam.discipline_id == user_discipline_id  # Use dynamic discipline
    ).first()
    
    if not exam:
        raise HTTPException(status_code=404, detail="Note not found or access denied")
    
    questions = db.query(Question).filter(Question.exam_id == exam_id).all()
    return {
        "id": exam.id,
        "title": exam.title,
        "discipline_id": exam.discipline_id,
        "time_limit": exam.time_limit,
        "source": exam.source,
        "questions": [
            {
                "text": q.text,
                "options": q.options,
                "correct_idx": q.correct_idx,
                "rationale": q.rationale
            } for q in questions
        ]
    }


@app.post("/exam/submit")
def submit_exam_results(
    exam_data: dict = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Minimal exam submission endpoint"""
    try:
        # Get exam details
        exam = db.query(Exam).filter(Exam.id == exam_data.get("exam_id")).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Note not found")
        
        # Store in user_activity
        activity = log_activity(db, current_user.id, "exam_completed", {
            "exam_id": exam_data.get("exam_id"),
            "exam_title": exam.title,
            "score": exam_data.get("score"),
            "total_questions": exam_data.get("total_questions", 0),
            "percentage": exam_data.get("score", 0),
            "passed": exam_data.get("score", 0) >= 70,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            "message": "Exam results saved successfully",
            "activity_id": activity.id,
            "score": exam_data.get("score")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving results: {str(e)}")





@app.post("/exam")
def create_exam_singular(
    exam_data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Create a new singular exam (study materials)"""
    try:
        exam_id = exam_data.get("id")
        title = exam_data.get("title")
        discipline_id = exam_data.get("discipline_id")
        time_limit = exam_data.get("time_limit", 50)
        source = "singular"  # Always singular for this endpoint
        questions_data = exam_data.get("questions", [])
        media_info = exam_data.get("media_info", {})  # NEW: Get media info if provided
        
        print(f"📥 Creating exam: {title}")
        print(f"🖼️  Media info: {media_info}")  # NEW: Log media info
        
        # Check if exam already exists
        existing_exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if existing_exam:
            return {"msg": f"Exam {exam_id} already exists"}
        
        # Create exam - JUST ADD MEDIA INFO TO EXISTING LOGIC
        exam = Exam(
            id=exam_id,
            title=title,
            discipline_id=discipline_id,
            time_limit=time_limit,
            source=source,
            is_released=True,  # Auto-release study materials
            # If your Exam model has media_info field, add this:
            # media_info=media_info  
        )
        db.add(exam)
        db.commit()
        
        # Create questions - NO CHANGES NEEDED HERE
        for q_data in questions_data:
            question = Question(
                id=q_data.get("id", str(uuid.uuid4())),
                exam_id=exam_id,
                text=q_data.get("text", ""),
                options=q_data.get("options", []),
                correct_idx=q_data.get("correct_idx", -1),
                rationale=q_data.get("rationale")
            )
            db.add(question)
        
        db.commit()
        
        # RETURN MEDIA INFO IN RESPONSE
        return {
            "msg": "Singular exam created successfully",
            "exam_id": exam_id,
            "questions_count": len(questions_data),
            "images_count": media_info.get("images_count", 0),  # NEW
            "tables_count": media_info.get("tables_count", 0),  # NEW
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating exam: {str(e)}")





# =============================================================================
#  NOTES ENDPOINTS ENDS HERE
# =============================================================================


# =============================================================================
# ADMIN ENDPOINTS - START
# =============================================================================




@app.get("/admin/users")
def admin_list_users(
    status: Optional[UserStatus] = Query(None),
    db: Session = Depends(get_db)
):
    """Admin endpoint to list users with filtering by status"""
    query = db.query(User)
    if status:
        query = query.filter(User.status == status)
    
    users = query.order_by(User.created_at.desc()).all()
    
    result = []
    for user in users:
        discipline_id = get_user_discipline_id(user)
        result.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "profession": user.profession,
            "specialist_type": user.specialist_type,
            "discipline_id": discipline_id,  # NEW: Include calculated discipline_id
            "status": user.status,
            "created_at": user.created_at,
            "approved_at": user.approved_at,
            # ✅ ADD THIS LINE:
            "premium_features": user.premium_features
        })
    
    return result

@app.post("/admin/users/{user_id}/approve")
def admin_approve_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Admin endpoint to approve a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = UserStatus.APPROVED
    user.approved_at = datetime.utcnow()
    db.commit()
    
    discipline_id = get_user_discipline_id(user)
    log_activity(db, user.id, "account_approved", {
        "approved_by": "admin",
        "discipline_id": discipline_id
    })
    
    return {
        "msg": f"User {user.email} approved successfully",
        "user_id": user.id,
        "status": user.status,
        "discipline_id": discipline_id,  # NEW: Return discipline_id
        "approved_at": user.approved_at
    }

@app.post("/admin/users/{user_id}/reject")
def admin_reject_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Admin endpoint to reject a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = UserStatus.REJECTED
    db.commit()
    
    discipline_id = get_user_discipline_id(user)
    log_activity(db, user.id, "account_rejected", {
        "rejected_by": "admin",
        "discipline_id": discipline_id
    })
    
    return {
        "msg": f"User {user.email} rejected",
        "user_id": user.id,
        "status": user.status,
        "discipline_id": discipline_id  # NEW: Return discipline_id
    }

# ADD AUTO LABELING ENDPOINT


@app.post("/admin/auto-label-questions")
def run_auto_labeling(db: Session = Depends(get_db)):
    """Automatically label unlabeled questions with topics"""
    try:
        updated_count = auto_label_questions(db)
        return {
            "success": True,
            "message": f"Auto-labeled {updated_count} questions with topics",
            "updated_count": updated_count
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error during auto-labeling: {str(e)}",
            "updated_count": 0
        }



# PUT THE DIAGNOSTIC ENDPOINT RIGHT HERE ↓

@app.get("/admin/question-label-status")
def get_question_label_status(db: Session = Depends(get_db)):
    """Check how many questions are labeled vs unlabeled"""
    total = db.query(Question).count()
    labeled = db.query(Question).filter(Question.topic.isnot(None)).count()
    unlabeled = total - labeled
    
    topics = db.query(Question.topic, func.count(Question.id)).filter(
        Question.topic.isnot(None)
    ).group_by(Question.topic).all()
    
    # Get questions by difficulty
    difficulties = db.query(Question.difficulty, func.count(Question.id)).filter(
        Question.difficulty.isnot(None)
    ).group_by(Question.difficulty).all()
    
    return {
        "total_questions": total,
        "labeled_questions": labeled,
        "unlabeled_questions": unlabeled,
        "labeling_percentage": round((labeled / total * 100), 2) if total > 0 else 0,
        "topics_breakdown": dict(topics),
        "difficulty_breakdown": dict(difficulties),
        "ready_for_smart_quiz": labeled >= 10  # Need at least 10 labeled questions
    }



@app.get("/admin/question-source-breakdown")
def get_question_source_breakdown(db: Session = Depends(get_db)):
    """Check where all these questions are coming from"""
    
    # Count questions by exam source
    source_stats = db.query(
        Exam.source,
        func.count(Question.id),
        func.count(case((Question.topic.isnot(None), 1))),  # labeled count
        func.count(case((Question.topic.is_(None), 1)))     # unlabeled count
    ).join(Question).group_by(Exam.source).all()
    
    # Get detailed breakdown
    detailed_stats = []
    for source, total, labeled, unlabeled in source_stats:
        exams = db.query(Exam).filter(Exam.source == source).all()
        detailed_stats.append({
            "source": source,
            "total_questions": total,
            "labeled_questions": labeled,
            "unlabeled_questions": unlabeled,
            "exam_count": len(exams),
            "exam_titles": [exam.title for exam in exams[:5]]  # First 5 exam titles
        })
    
    return {
        "question_breakdown": detailed_stats,
        "total_questions_across_all_sources": sum([stat["total_questions"] for stat in detailed_stats])
    }


@app.get("/admin/exams")
def admin_list_exams(
    discipline_id: str = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Exam)
    if discipline_id:
        query = query.filter(Exam.discipline_id == discipline_id)
    
    exams = query.all()
    return [
        {
            "id": exam.id,
            "title": exam.title,
            "discipline_id": exam.discipline_id,
            "source": exam.source,
            "is_released": exam.is_released,
            "release_date": exam.release_date,
            "time_limit": exam.time_limit,
            "question_count": len(exam.questions) if exam.questions else 0
        }
        for exam in exams
    ]

@app.post("/admin/exams/{exam_id}/release")
def release_exam(
    exam_id: str,
    db: Session = Depends(get_db)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    exam.is_released = True
    exam.release_date = datetime.utcnow()
    db.commit()
    
    return {
        "msg": f"Exam '{exam.title}' released", 
        "release_date": exam.release_date,
        "is_released": True
    }

@app.post("/admin/exams/{exam_id}/unrelease")
def unrelease_exam(exam_id: str, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    
    exam.is_released = False
    db.commit()
    return {"msg": f"Exam '{exam.title}' recalled", "is_released": False}


@app.get("/admin/force-update-schema")
def admin_force_update_schema(db: Session = Depends(get_db)):
    """Admin endpoint to force update database schema"""
    success = force_update_schema()
    if success:
        return {"message": "Database schema updated successfully. All data was reset."}
    else:
        return {"message": "Failed to update database schema"}


# NEW: Password reset endpoint
@app.post("/admin/users/{user_id}/reset-password")
def admin_reset_user_password(
    user_id: int,
    new_password: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """Admin endpoint to reset user password"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Hash and set new password
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    # Log the action
    log_activity(db, user.id, "password_reset_by_admin", {
        "reset_by": "admin",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        "message": f"Password reset successfully for {user.email}",
        "user_id": user.id,
        "email": user.email
    }

# NEW: Exam results viewing
@app.get("/admin/exam-results")
def admin_get_all_exam_results(
    user_id: Optional[int] = Query(None),
    exam_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Admin endpoint to view all exam results with filtering"""
    query = db.query(UserActivity).filter(UserActivity.activity_type == "exam_completed")
    
    if user_id:
        query = query.filter(UserActivity.user_id == user_id)
    
    activities = query.order_by(UserActivity.timestamp.desc()).all()
    
    results = []
    for activity in activities:
        details = activity.details or {}
        user = db.query(User).filter(User.id == activity.user_id).first()
        
        results.append({
            "id": activity.id,
            "user_id": activity.user_id,
            "user_email": user.email if user else "Unknown",
            "user_name": user.full_name if user else "Unknown",
            "user_profession": user.profession if user else "Unknown",
            "exam_id": details.get("exam_id", "Unknown"),
            "exam_title": details.get("exam_title", "Unknown Exam"),
            "score": details.get("score", 0),
            "total_questions": details.get("total_questions", 0),
            "percentage": details.get("percentage", 0),
            "passed": details.get("passed", False),
            "completed_at": activity.timestamp,
            "user_answers": details.get("user_answers", {})  # ADDED: Return user answers
        })
    
    # Filter by exam_id if provided
    if exam_id:
        results = [r for r in results if exam_id.lower() in r["exam_id"].lower()]
    
    return results

# NEW: User exam results
@app.get("/admin/users/{user_id}/exam-results")
def admin_get_user_exam_results(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Admin endpoint to view specific user's exam results"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    activities = db.query(UserActivity).filter(
        UserActivity.user_id == user_id,
        UserActivity.activity_type == "exam_completed"
    ).order_by(UserActivity.timestamp.desc()).all()
    
    exam_results = []
    for activity in activities:
        details = activity.details or {}
        exam_results.append({
            "exam_id": details.get("exam_id", "Unknown"),
            "exam_title": details.get("exam_title", "Unknown Exam"),
            "score": details.get("score", 0),
            "total_questions": details.get("total_questions", 0),
            "percentage": details.get("percentage", 0),
            "passed": details.get("passed", False),
            "completed_at": activity.timestamp
        })
    
    return {
        "user_info": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "profession": user.profession,
            "status": user.status
        },
        "exam_results": exam_results,
        "total_exams": len(exam_results)
    }


# DELETE SPECIfic NOTE

@app.delete("/admin/exam/{exam_id}")
def delete_singular_exam(
    exam_id: str,
    db: Session = Depends(get_db)
):
    """Delete a study note (singular exam)"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Study note not found")
    
    db.delete(exam)
    db.commit()
    
    return {"msg": f"Study note '{exam.title}' deleted successfully"}



@app.delete("/admin/exam/discipline/{discipline}")
def delete_study_notes_by_discipline(
    discipline: str,
    db: Session = Depends(get_db)
):
    """Delete all study notes (singular exams) for a specific discipline"""
    # Find all singular exams (study notes) for this discipline
    exams = db.query(Exam).filter(
        Exam.discipline_id == discipline,
        Exam.source == "singular"
    ).all()
    
    if not exams:
        raise HTTPException(status_code=404, detail=f"No study notes found for discipline: {discipline}")
    
    # SIMPLE DELETE - just like the working function
    deleted_count = db.query(Exam).filter(
        Exam.discipline_id == discipline,
        Exam.source == "singular"
    ).delete()
    
    db.commit()
    
    return {
        "msg": f"Deleted {deleted_count} study notes for discipline: {discipline}",
        "deleted_count": deleted_count,
        "discipline": discipline
    }



# ADD THIS TEMPORARY TEST ENDPOINT TO YOUR BACKEND
@app.delete("/admin/test-delete")
def test_delete_endpoint():
    return {"message": "DELETE endpoint is working!"}


@app.api_route("/admin/exam/{exam_id}", methods=["GET", "DELETE", "OPTIONS"])
def exam_options(exam_id: str):
    return {"methods": ["GET", "DELETE"]}




# NEW: User impersonation
@app.post("/admin/users/{user_id}/impersonate")
def admin_impersonate_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Admin endpoint to generate login token for any user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is approved
    if user.status != UserStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Cannot impersonate unapproved user")
    
    # Create access token for the target user
    access_token_expires = timedelta(hours=24)  # Longer expiry for admin convenience
    access_token = create_access_token(
        data={"user_id": user.id}, expires_delta=access_token_expires
    )
    
    # Log the impersonation activity
    log_activity(db, user.id, "admin_impersonation", {
        "impersonated_by": "admin",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "profession": user.profession
        },
        "message": f"You are now logged in as {user.email}"
    }

# NEW: User activity monitoring
@app.get("/admin/users/{user_id}/activity")
def admin_get_user_activity(
    user_id: int,
    activity_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Admin endpoint to view any user's complete activity"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    query = db.query(UserActivity).filter(UserActivity.user_id == user_id)
    
    if activity_type:
        query = query.filter(UserActivity.activity_type == activity_type)
    
    activities = query.order_by(UserActivity.timestamp.desc()).limit(limit).all()
    
    return {
        "user_info": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "profession": user.profession,
            "status": user.status
        },
        "activities": [
            {
                "activity_type": a.activity_type,
                "timestamp": a.timestamp,
                "details": a.details
            }
            for a in activities
        ],
        "total_activities": len(activities)
    }

# NEW: Admin dashboard
@app.get("/admin/dashboard")
def admin_dashboard_summary(db: Session = Depends(get_db)):
    """Admin dashboard with overall statistics"""
    # User statistics
    total_users = db.query(User).count()
    pending_users = db.query(User).filter(User.status == UserStatus.PENDING).count()
    approved_users = db.query(User).filter(User.status == UserStatus.APPROVED).count()
    
    # Exam results statistics
    exam_activities = db.query(UserActivity).filter(
        UserActivity.activity_type == "exam_completed"
    ).all()
    
    total_exams = len(exam_activities)
    passed_exams = sum(1 for a in exam_activities if a.details and a.details.get("passed"))
    
    # Recent activity
    recent_activities = db.query(UserActivity).order_by(
        UserActivity.timestamp.desc()
    ).limit(10).all()
    
    recent_activity_data = []
    for a in recent_activities:
        user = db.query(User).filter(User.id == a.user_id).first()
        recent_activity_data.append({
            "user_id": a.user_id,
            "user_email": user.email if user else "Unknown",
            "activity_type": a.activity_type,
            "timestamp": a.timestamp
        })
    
    return {
        "user_stats": {
            "total_users": total_users,
            "pending_approval": pending_users,
            "approved_users": approved_users
        },
        "exam_stats": {
            "total_exams_taken": total_exams,
            "passed_exams": passed_exams,
            "failed_exams": total_exams - passed_exams,
            "pass_rate": (passed_exams / total_exams * 100) if total_exams > 0 else 0,
            "average_percentage": 0  # You can calculate this if needed
        },
        "recent_activity": recent_activity_data
    }



@app.post("/admin/users/{user_id}/block")
async def block_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = "blocked"
    db.commit()
    
    return {"message": f"User {user.email} blocked successfully"}




@app.post("/admin/users/{user_id}/unblock")
async def unblock_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = "approved"
    db.commit()
    
    return {"message": f"User {user.email} unblocked successfully"}


# =============================================================================
# END OF ADMIN ENDPOINTS
# =============================================================================





# =============================================================================
# QUIZ ENDPOINTS START HERE
# =============================================================================



# Auto-label questions on server startup
def initialize_quiz_questions():
    """Auto-label quiz questions when server starts"""
    print("🔄 Checking quiz questions...")
    db = SessionLocal()
    try:
        # Count quiz questions (from plural exams)
        total_quiz_questions = db.query(Question).join(Exam).filter(
            Exam.source == "plural"
        ).count()
        
        # Count labeled quiz questions
        labeled_quiz_questions = db.query(Question).join(Exam).filter(
            Exam.source == "plural",
            Question.topic.isnot(None)
        ).count()
        
        print(f"📊 Quiz Questions: {labeled_quiz_questions}/{total_quiz_questions} labeled")
        
        # Auto-label if no labeled questions
        if labeled_quiz_questions == 0 and total_quiz_questions > 0:
            print("🎯 Auto-labeling quiz questions...")
            updated_count = auto_label_questions(db)
            print(f"✅ Auto-labeled {updated_count} quiz questions")
        elif total_quiz_questions == 0:
            print("⚠️  No quiz questions found. Please upload some quizzes first.")
        else:
            print("✅ Quiz questions are ready for Smart Quiz!")
            
    except Exception as e:
        print(f"❌ Error initializing quiz questions: {e}")
    finally:
        db.close()

# Call this function when app starts
initialize_quiz_questions()




async def get_all_exams(db: Session = Depends(get_keamed_db)):
    """Get all exams from KeamedExam database"""
    try:
        # Get all exams from keamed_exams table
        exams = db.execute(text("SELECT * FROM keamed_exams")).fetchall()
        
        result = []
        for exam in exams:
            exam_dict = dict(exam._mapping)
            
            # Get question count for each exam
            question_count = db.execute(
                text("SELECT COUNT(*) FROM keamed_questions WHERE exam_id = :eid"),
                {"eid": exam_dict['id']}
            ).fetchone()[0]
            
            # Get questions for each exam
            questions = db.execute(
                text("SELECT * FROM keamed_questions WHERE exam_id = :eid"),
                {"eid": exam_dict['id']}
            ).fetchall()
            
            # Convert questions to proper format
            question_list = []
            for question in questions:
                question_dict = dict(question._mapping)
                question_list.append({
                    'id': question_dict['id'],
                    'question_text': question_dict['question_text'],
                    'options': json.loads(question_dict['options']),
                    'correct_answer': question_dict['correct_answer']
                })
            
            exam_dict['question_count'] = question_count
            exam_dict['questions'] = question_list
            result.append(exam_dict)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# KEA - MED Specific ENDPOINTS

from sqlalchemy import text
from datetime import datetime
import json
from typing import Optional
import re
from app.database import get_keamed_db  # ADDED IMPORT

# ===== CONFIG ENDPOINTS =====
@app.get("/keamedexam/config")
def get_keamedexam_config(db: Session = Depends(get_keamed_db)):  # CHANGED
    try:
        # Get configuration from keamed_exams table instead of keamed_config
        configs = db.execute(text('''
            SELECT exam_type, time_per_question, total_questions 
            FROM keamed_exams 
            WHERE is_active = TRUE
            GROUP BY exam_type, time_per_question, total_questions
        ''')).fetchall()
        
        config_dict = {}
        for row in configs:
            config_dict[row[0]] = {
                'exam_type': row[0],
                'time_per_question': row[1],
                'total_questions': row[2]
            }
        return config_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/keamedexam/config")
def create_keamedexam_config(config_data: dict, db: Session = Depends(get_keamed_db)):  # CHANGED
    try:
        required_fields = ['exam_type', 'time_per_question', 'total_questions']
        for field in required_fields:
            if field not in config_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Update ALL exams of this type with the new configuration
        db.execute(
            text("UPDATE keamed_exams SET time_per_question = :tq, total_questions = :tqs WHERE exam_type = :et"),
            {"tq": config_data['time_per_question'], "tqs": config_data['total_questions'], "et": config_data['exam_type']}
        )
        
        db.commit()
        return {"msg": f"Exam configuration updated for all {config_data['exam_type']} exams", "exam_type": config_data['exam_type']}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ===== EXAM MANAGEMENT =====

@app.post("/keamedexam/start")
def start_keamedexam(data: dict, db: Session = Depends(get_keamed_db)):  # CHANGED
    try:
        exam_type = data.get('exam_type')
        
        # Get available exams for this exam_type from keamed_exams table
        exams = db.execute(
            text('SELECT * FROM keamed_exams WHERE exam_type = :exam_type AND is_active = TRUE LIMIT 1'), 
            {"exam_type": exam_type}
        ).fetchall()
        
        if not exams:
            raise HTTPException(status_code=404, detail='No active exams found for this type')
            
        exam = exams[0]
        exam_dict = dict(exam._mapping)
        
        # Calculate total time from exam-specific configuration
        total_time = exam_dict['total_questions'] * exam_dict['time_per_question'] * 60
        
        return {
            'exam_config': {
                'exam_type': exam_dict['exam_type'],
                'time_per_question': exam_dict['time_per_question'], 
                'total_questions': exam_dict['total_questions'],
                'exam_title': exam_dict['title'],
                'exam_id': exam_dict['id']
            },
            'total_time_seconds': total_time
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/keamedexam/submit")
def submit_keamedexam(data: dict, db: Session = Depends(get_keamed_db)):  # CHANGED
    try:
        # Extract data
        user_id = data['user_id']
        user_name = data['user_name'] 
        exam_id = data['exam_id']
        user_answers = data['user_answers']
        time_spent = data.get('time_spent', 0)
        
        # Get exam details from keamed_exams table
        exam = db.execute(
            text('SELECT * FROM keamed_exams WHERE id = :exam_id'),
            {"exam_id": exam_id}
        ).fetchone()
        
        if not exam:
            raise HTTPException(status_code=404, detail='Exam not found')
        
        # Convert exam tuple to dict
        exam_dict = dict(exam._mapping)
        
        # Get all questions for this exam from keamed_questions table
        questions = db.execute(
            text('SELECT * FROM keamed_questions WHERE exam_id = :exam_id'),
            {"exam_id": exam_id}
        ).fetchall()
        
        # Calculate score by comparing answers
        correct_count = 0
        topic_performance = {}
        
        for user_answer in user_answers:
            question_id = user_answer['question_id']
            selected_option = user_answer['selected_option']
            
            # Find the question
            question = next((q for q in questions if str(q[0]) == str(question_id)), None)
            if question:
                question_dict = dict(question._mapping)
                correct_answer = question_dict.get('correct_answer')
                
                if selected_option == correct_answer:
                    correct_count += 1
        
        total_questions = len(questions)
        score = correct_count
        
        # Store results in keamed_results table
        db.execute(text('''
            INSERT INTO keamed_results 
            (user_id, user_name, user_profession, exam_type, exam_id, exam_title, 
             score, total_questions, time_spent, user_answers, topic_performance)
            VALUES (:user_id, :user_name, :user_profession, :exam_type, :exam_id, :exam_title,
                    :score, :total_questions, :time_spent, :user_answers, :topic_performance)
        '''), {
            "user_id": user_id,
            "user_name": user_name,
            "user_profession": data.get('user_profession', ''),
            "exam_type": exam_dict['exam_type'],
            "exam_id": exam_id,
            "exam_title": exam_dict['title'],
            "score": score,
            "total_questions": total_questions,
            "time_spent": time_spent,
            "user_answers": json.dumps(user_answers),
            "topic_performance": json.dumps(topic_performance)
        })
        
        db.commit()
        return {'status': 'success', 'score': score, 'correct_answers': correct_count, 'total_questions': total_questions}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ===== ADMIN ENDPOINTS =====

@app.get("/admin/keamedexam/exams")
def get_keamed_exams(discipline: Optional[str] = Query(None), db: Session = Depends(get_keamed_db)):  # CHANGED
    try:
        if discipline:
            exams = db.execute(
                text("SELECT * FROM keamed_exams WHERE discipline_id = :disc"), 
                {"disc": discipline}
            ).fetchall()
        else:
            exams = db.execute(text("SELECT * FROM keamed_exams")).fetchall()
        
        result = []
        for exam in exams:
            exam_dict = dict(exam._mapping)
            
            # FIXED: Now using keamed_questions table
            question_count = db.execute(
                text("SELECT COUNT(*) FROM keamed_questions WHERE exam_id = :eid"),
                {"eid": exam_dict['id']}
            ).fetchone()[0]
            
            exam_dict['question_count'] = question_count
            result.append(exam_dict)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.get("/admin/keamedexam/exams/{exam_id}")
def get_exam_by_id(exam_id: str, db: Session = Depends(get_keamed_db)):
    """Get specific exam by ID from KeamedExam system"""
    try:
        # Get exam from database directly
        exam = db.execute(
            text("SELECT * FROM keamed_exams WHERE id = :eid"),
            {"eid": exam_id}
        ).fetchone()
        
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        exam_dict = dict(exam._mapping)
        
        # Get questions for this exam
        questions = db.execute(
            text("SELECT * FROM keamed_questions WHERE exam_id = :eid"),
            {"eid": exam_id}
        ).fetchall()
        
        # FIXED: Proper options handling
        question_list = []
        for question in questions:
            question_dict = dict(question._mapping)
            
            options_data = question_dict['options']
            
            # DEBUG
            print(f"OPTIONS RAW: {options_data}")
            print(f"OPTIONS TYPE: {type(options_data)}")
            
            # Handle different data types
            if options_data is None:
                final_options = []
            elif isinstance(options_data, list):
                final_options = options_data
            elif isinstance(options_data, str):
                try:
                    # Parse JSON string to list
                    final_options = json.loads(options_data)
                except json.JSONDecodeError:
                    final_options = []
            else:
                final_options = []
            
            # Ensure it's always a list
            if not isinstance(final_options, list):
                final_options = []
            
            print(f"FINAL OPTIONS: {final_options}")
            
            question_list.append({
                'text': question_dict['question_text'],
                'options': final_options,  # ✅ This must be a list
                'correct_idx': int(question_dict['correct_answer'])
            })
        
        exam_dict['questions'] = question_list
        exam_dict['question_count'] = len(questions)
        
        return exam_dict
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/admin/keamedexam/exams/{exam_id}/questions")
async def get_exam_questions(exam_id: str):
    """Get questions for a specific exam from KeamedExam system"""
    try:
        # Get all exams from KeamedExam
        exams = await get_all_exams()  # Your existing function
        
        # Find the specific exam
        exam = next((e for e in exams if e.get('id') == exam_id), None)
        
        if not exam:
            raise HTTPException(status_code=404, detail="Exam not found")
        
        # Return just the questions
        questions = exam.get('questions', [])
        return questions
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/keamedexam/exams/search")
async def search_exams(title: str = None, discipline_id: str = None):
    """Search exams by title and/or discipline_id"""
    try:
        # Get all exams from your database
        exams = await get_all_exams()  # Your existing function
        
        # Filter exams based on query parameters
        filtered_exams = exams
        
        if title:
            filtered_exams = [exam for exam in filtered_exams 
                            if title.lower() in exam.get('title', '').lower()]
        
        if discipline_id:
            filtered_exams = [exam for exam in filtered_exams 
                            if exam.get('discipline_id') == discipline_id]
        
        return filtered_exams
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/keamedexam/users/{user_id}/exams")
async def get_user_exam_access(user_id: str):
    """Get exams that a specific user has access to"""
    try:
        # Your logic to get user's exam access
        user_exams = await get_user_exams(user_id)
        return user_exams
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/keamedexam/users/{user_id}/exams/{exam_id}/grant-access")
async def grant_exam_access(user_id: str, exam_id: str):
    """Grant exam access to a user"""
    try:
        # Your logic to grant exam access
        result = await grant_user_exam_access(user_id, exam_id)
        return {"status": "success", "msg": "Exam access granted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/keamedexam/users/{user_id}/exams/{exam_id}/revoke-access")
async def revoke_exam_access(user_id: str, exam_id: str):
    """Revoke exam access from a user"""
    try:
        # Your logic to revoke exam access
        result = await revoke_user_exam_access(user_id, exam_id)
        return {"status": "success", "msg": "Exam access revoked"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/admin/keamedexam/exams/{exam_id}/release")
async def release_exam(exam_id: str):
    """Release an exam in KeamedExam system"""
    try:
        # Your logic to release exam
        result = await release_keamed_exam(exam_id)
        return {"status": "success", "msg": "Exam released", "release_date": "2024-01-01"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@app.post("/admin/keamedexam/exams/{exam_id}/unrelease")
async def unrelease_exam(exam_id: str):
    """Unrelease an exam in KeamedExam system"""
    try:
        # Your logic to unrelease exam
        result = await unrelease_keamed_exam(exam_id)
        return {"status": "success", "msg": "Exam unreleased"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/keamedexam/results/enhanced")
def get_enhanced_keamed_results(
    user_id: Optional[str] = Query(None), 
    exam_id: Optional[str] = Query(None),
    db: Session = Depends(get_keamed_db)  # CHANGED
):
    try:
        # FIXED: Now using keamed_results table
        query = 'SELECT kr.*, ke.title as exam_title FROM keamed_results kr LEFT JOIN keamed_exams ke ON kr.exam_id = ke.id WHERE 1=1'
        params = {}
        
        if user_id:
            query += ' AND kr.user_id = :user_id'
            params['user_id'] = user_id
        if exam_id:
            query += ' AND kr.exam_id = :exam_id'
            params['exam_id'] = exam_id
            
        results = db.execute(text(query + ' ORDER BY kr.timestamp DESC'), params).fetchall()
        return [dict(row._mapping) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/keamedexam/users")
def get_keamedexam_users(db: Session = Depends(get_keamed_db)):  # CHANGED
    try:
        # FIXED: Now using keamed_results table
        users = db.execute(text('''
            SELECT DISTINCT user_id, user_name, user_profession,
                   COUNT(*) as exam_count
            FROM keamed_results 
            GROUP BY user_id, user_name, user_profession
        ''')).fetchall()
        return [dict(row._mapping) for row in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/keamedexam/exams/{exam_id}/activate")
def activate_keamed_exam(exam_id: str, db: Session = Depends(get_keamed_db)):  # CHANGED
    try:
        # Check if exam exists in keamed_exams table
        exam = db.execute(
            text("SELECT * FROM keamed_exams WHERE id = :eid"), 
            {"eid": exam_id}
        ).fetchone()
        
        if not exam:
            raise HTTPException(status_code=404, detail='Exam not found')
        
        # Update is_active flag in keamed_exams table
        db.execute(
            text("UPDATE keamed_exams SET is_active = TRUE WHERE id = :eid"), 
            {"eid": exam_id}
        )
        
        db.commit()
        return {'msg': f'Exam {exam_id} activated'}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/keamedexam/exams/{exam_id}/deactivate")
def deactivate_keamed_exam(exam_id: str, db: Session = Depends(get_keamed_db)):  # CHANGED
    try:
        # Update is_active flag in keamed_exams table
        db.execute(
            text("UPDATE keamed_exams SET is_active = FALSE WHERE id = :eid"), 
            {"eid": exam_id}
        )
        db.commit()
        return {'msg': f'Exam {exam_id} deactivated'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/keamedexam/exams/{exam_id}")
def delete_keamed_exam(exam_id: str, db: Session = Depends(get_keamed_db)):  # CHANGED
    try:
        # Delete from keamed_exams table
        db.execute(text('DELETE FROM keamed_exams WHERE id = :eid'), {"eid": exam_id})
        # Also delete related questions from keamed_questions table
        db.execute(text('DELETE FROM keamed_questions WHERE exam_id = :eid'), {"eid": exam_id})
        db.commit()
        return {'msg': f'Exam {exam_id} deleted'}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/keamedexam/list")
def list_keamed_exams(db: Session = Depends(get_keamed_db)):  # CHANGED
    try:
        # Get only active exams from keamed_exams table
        exams = db.execute(text('SELECT * FROM keamed_exams WHERE is_active = TRUE')).fetchall()
        return [dict(exam._mapping) for exam in exams]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/keamedexam/results")
def get_keamedexam_results(db: Session = Depends(get_keamed_db)):  # CHANGED
    try:
        # FIXED: Now using keamed_results table
        results = db.execute(text('''
            SELECT user_name, user_profession, exam_type, exam_id, score, timestamp 
            FROM keamed_results 
            ORDER BY timestamp DESC
        ''')).fetchall()
        return [dict(row._mapping) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/keamedexam/stats")
def get_keamed_stats(db: Session = Depends(get_keamed_db)):  # CHANGED
    try:
        # FIXED: Now using keamed_results table
        total_exams = db.execute(text('SELECT COUNT(*) as count FROM keamed_results')).fetchone()[0]
        unique_users = db.execute(text('SELECT COUNT(DISTINCT user_id) as count FROM keamed_results')).fetchone()[0]
        avg_score = db.execute(text('SELECT AVG(score) as avg FROM keamed_results')).fetchone()[0] or 0
        
        exams_by_discipline = db.execute(text('''
            SELECT ke.discipline_id, COUNT(*) as count FROM keamed_results kr 
            JOIN keamed_exams ke ON kr.exam_id = ke.id GROUP BY ke.discipline_id
        ''')).fetchall()
        
        return {
            'total_exams_taken': total_exams,
            'unique_users': unique_users,
            'average_score': round(avg_score, 2),
            'exams_by_discipline': {row[0]: row[1] for row in exams_by_discipline}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

        

@app.post("/admin/keamedexam/exams")
def upload_keamed_exam(exam_data: dict, db: Session = Depends(get_keamed_db)):
    try:
        # Use the ID from upload script
        exam_id = exam_data['id']
        
        # Insert exam
        db.execute(
            text("""
                INSERT INTO keamed_exams 
                (id, title, discipline_id, exam_type, is_active) 
                VALUES (:id, :title, :disc, :exam_type, :active)
            """),
            {
                "id": exam_id, 
                "title": exam_data['title'], 
                "disc": exam_data['discipline_id'],
                "exam_type": exam_data.get('exam_type', 'custom'),
                "active": exam_data.get('is_released', False)
            }
        )
        
        # Insert questions INTO keamed_questions table
        for i, question in enumerate(exam_data.get('questions', [])):
            question_id = f"{exam_id}_q{i+1}"
            
            # FIXED: Use the options array from upload script
            options_array = question.get('options', [])
            # Ensure we have at least 4 options (pad with empty strings if needed)
            while len(options_array) < 4:
                options_array.append('')
            
            db.execute(
                text("""
                    INSERT INTO keamed_questions 
                    (id, exam_id, question_text, options, correct_answer)
                    VALUES (:id, :eid, :question_text, :options, :correct_answer)
                """),
                {
                    "id": question_id,
                    "eid": exam_id, 
                    "question_text": str(question.get('text', '')),  # ✅ Changed from 'question_text' to 'text'
                    "options": json.dumps(options_array),  # ✅ Use the options array directly
                    "correct_answer": str(question.get('correct_idx', 0))  # ✅ Changed from 'correct_index' to 'correct_idx'
                }
            )
        
        db.commit()
        return {"msg": "Keamed exam uploaded successfully", "exam_id": exam_id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/keamedexam/debug/{exam_id}")
def debug_exam(exam_id: str, db: Session = Depends(get_keamed_db)):
    """Debug endpoint to check what's in the database"""
    try:
        # Check if exam exists
        exam = db.execute(
            text("SELECT * FROM keamed_exams WHERE id = :eid"),
            {"eid": exam_id}
        ).fetchone()
        
        if not exam:
            return {"error": "Exam not found in keamed_exams", "exam_id": exam_id}
        
        exam_dict = dict(exam._mapping)
        
        # Check questions
        questions = db.execute(
            text("SELECT * FROM keamed_questions WHERE exam_id = :eid"),
            {"eid": exam_id}
        ).fetchall()
        
        return {
            "exam_found": True,
            "exam_data": exam_dict,
            "question_count": len(questions),
            "questions_sample": [dict(q._mapping) for q in questions[:2]] if questions else []
        }
        
    except Exception as e:
        return {"error": str(e)}



@app.get("/debug/quiz/{exam_id}")
def debug_quiz(exam_id: str, db: Session = Depends(get_db)):
    """Debug endpoint to check quiz status"""
    print(f"🔍 DEBUG QUIZ LOOKUP: {exam_id}")
    
    # Check all exams with this ID
    all_exams = db.query(Exam).filter(Exam.id == exam_id).all()
    print(f"📊 FOUND {len(all_exams)} EXAMS WITH THIS ID:")
    
    for exam in all_exams:
        questions = db.query(Question).filter(Question.exam_id == exam_id).all()
        print(f"   - ID: {exam.id}")
        print(f"     Title: {exam.title}")
        print(f"     Source: {exam.source}")
        print(f"     Discipline: {exam.discipline_id}") 
        print(f"     Released: {exam.is_released}")
        print(f"     Questions: {len(questions)}")
    
    # Check what the intelligent endpoint would find
    intelligent_exam = db.query(Exam).filter(
        Exam.id == exam_id, 
        Exam.source == "intelligent"
    ).first()
    
    return {
        "total_exams_found": len(all_exams),
        "intelligent_exam_found": intelligent_exam is not None,
        "exams": [
            {
                "id": exam.id,
                "title": exam.title, 
                "source": exam.source,
                "discipline": exam.discipline_id,
                "released": exam.is_released,
                "question_count": db.query(Question).filter(Question.exam_id == exam.id).count()
            }
            for exam in all_exams
        ]
    }




# Continue from where we left off in main.py

# =============================================================================
# AI PROGRESS & ANALYTICS - CONTINUED
# =============================================================================

@app.get("/ai/progress/{user_id}")
async def get_user_ai_progress(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's AI training progress"""
    if str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Count simulation attempts
    sim_attempts = [
        attempt for attempt in simulation_attempts.values()
        if attempt["userId"] == user_id and attempt["completed"]
    ]
    
    # Count procedure attempts
    proc_attempts = [
        attempt for attempt in procedure_attempts.values()
        if attempt["userId"] == user_id and attempt["completed"]
    ]
    
    # Calculate averages
    sim_scores = [attempt.get("score", 0) for attempt in sim_attempts if "score" in attempt]
    proc_scores = [attempt.get("score", 0) for attempt in proc_attempts if "score" in attempt]
    
    avg_sim_score = sum(sim_scores) / len(sim_scores) if sim_scores else 0
    avg_proc_score = sum(proc_scores) / len(proc_scores) if proc_scores else 0
    
    # Get user's exam history to identify weak areas
    exam_activities = db.query(UserActivity).filter(
        UserActivity.user_id == current_user.id,
        UserActivity.activity_type == "exam_completed"
    ).all()
    
    # Simple analysis of weak areas (in production, use more sophisticated analysis)
    weak_areas = []
    strong_areas = []
    
    if exam_activities:
        # Mock analysis - in real app, analyze question topics
        weak_areas = ["clinical_skills", "pharmacology"]  # Placeholder
        strong_areas = ["anatomy", "patient_care"]  # Placeholder
    
    return {
        "userId": user_id,
        "simulationsCompleted": len(sim_attempts),
        "proceduresCompleted": len(proc_attempts),
        "totalScore": sum(sim_scores + proc_scores),
        "averageSimulationScore": round(avg_sim_score, 2),
        "averageProcedureScore": round(avg_proc_score, 2),
        "strongAreas": strong_areas,
        "weakAreas": weak_areas,
        "lastActive": datetime.utcnow().isoformat(),
        "weeklyGoals": {
            "simulations": 3,
            "procedures": 2,
            "targetScore": 80
        }
    }

@app.put("/ai/progress/{user_id}")
async def update_user_ai_progress(
    user_id: str,
    data: dict = Body(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user's AI progress (for future extension)"""
    if str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # This would update database records in production
    return {
        "success": True,
        "message": "Progress updated",
        "userId": user_id,
        "updatedFields": list(data.keys())
    }

@app.get("/ai/recommendations/{user_id}")
async def get_personalized_recommendations(
    user_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get personalized AI training recommendations"""
    if str(current_user.id) != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # In production, use AI to analyze user's weak areas and recommend
    # For now, return mock recommendations
    return {
        "recommendedSimulations": [
            {
                "id": "mock_sim_1",
                "title": "ICU Patient Deterioration",
                "specialty": "critical_care",
                "difficulty": "intermediate",
                "estimatedDuration": 20,
                "reason": "Focuses on your weak area: clinical_skills"
            }
        ],
        "recommendedProcedures": [
            {
                "id": "mock_proc_1",
                "title": "Advanced Airway Management",
                "specialty": "emergency",
                "difficulty": "advanced",
                "reason": "Builds on your pharmacology knowledge"
            }
        ],
        "focusAreas": ["clinical_skills", "pharmacology"]







    }

# =============================================================================
# AI CATALOG ENDPOINTS
# =============================================================================

@app.get("/ai/simulations/catalog")
async def get_simulation_catalog(
    specialty: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """Get available AI simulations catalog"""
    # In production, this would query a database
    # For now, return mock data
    mock_simulations = [
        {
            "id": "sim_cardiac_001",
            "title": "Acute Chest Pain Management",
            "specialty": "cardiology",
            "difficulty": "intermediate",
            "estimatedDuration": 25,
            "description": "Manage a patient presenting with acute chest pain",
            "learningPoints": ["ECG interpretation", "ACS management", "Medication administration"]
        },
        {
            "id": "sim_respiratory_001",
            "title": "Acute Respiratory Distress",
            "specialty": "pulmonary",
            "difficulty": "advanced",
            "estimatedDuration": 30,
            "description": "Manage a patient with acute respiratory failure",
            "learningPoints": ["Oxygen therapy", "Ventilator management", "Airway assessment"]
        },
        {
            "id": "sim_trauma_001",
            "title": "Multi-trauma Patient Assessment",
            "specialty": "emergency",
            "difficulty": "intermediate",
            "estimatedDuration": 20,
            "description": "Initial assessment and management of multi-trauma patient",
            "learningPoints": ["Primary survey", "Trauma triage", "Shock management"]
        }
    ]
    
    # Filter by specialty if provided
    if specialty:
        mock_simulations = [s for s in mock_simulations if s["specialty"] == specialty]
    
    # Filter by difficulty if provided
    if difficulty:
        mock_simulations = [s for s in mock_simulations if s["difficulty"] == difficulty]
    
    return {
        "simulations": mock_simulations[:limit],
        "count": len(mock_simulations[:limit]),
        "total": len(mock_simulations)
    }

@app.get("/ai/procedures/catalog")
async def get_procedure_catalog(
    specialty: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """Get available AI procedures catalog"""
    # In production, this would query a database
    mock_procedures = [
        {
            "id": "proc_iv_001",
            "title": "Peripheral IV Insertion",
            "specialty": "nursing",
            "difficulty": "beginner",
            "averageDuration": 600,
            "description": "Step-by-step guide for peripheral intravenous catheter insertion",
            "indications": ["Medication administration", "Fluid resuscitation", "Blood sampling"]
        },
        {
            "id": "proc_intubation_001",
            "title": "Endotracheal Intubation",
            "specialty": "anesthesia",
            "difficulty": "advanced",
            "averageDuration": 900,
            "description": "Advanced airway management technique",
            "indications": ["Airway protection", "Mechanical ventilation", "General anesthesia"]
        },
        {
            "id": "proc_wound_001",
            "title": "Wound Dressing and Care",
            "specialty": "wound_care",
            "difficulty": "intermediate",
            "averageDuration": 450,
            "description": "Proper wound assessment and dressing technique",
            "indications": ["Post-operative wounds", "Chronic wounds", "Traumatic injuries"]
        }
    ]
    
    # Filter by specialty if provided
    if specialty:
        mock_procedures = [p for p in mock_procedures if p["specialty"] == specialty]
    
    # Filter by difficulty if provided
    if difficulty:
        mock_procedures = [p for p in mock_procedures if p["difficulty"] == difficulty]
    
    return {
        "procedures": mock_procedures[:limit],
        "count": len(mock_procedures[:limit]),
        "total": len(mock_procedures)
    }

# =============================================================================
# ADMIN AI ENDPOINTS
# =============================================================================

@app.get("/admin/ai/usage")
async def admin_get_ai_usage(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Admin endpoint to view AI usage analytics"""
    # Check if user is admin (simplified check)
    if current_user.profession != "admin":  # You might have a different admin check
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Count simulation attempts
    sim_count = len([a for a in simulation_attempts.values() if a["completed"]])
    proc_count = len([a for a in procedure_attempts.values() if a["completed"]])
    
    # Calculate average scores
    sim_scores = [a.get("score", 0) for a in simulation_attempts.values() if a.get("completed")]
    proc_scores = [a.get("score", 0) for a in procedure_attempts.values() if a.get("completed")]
    
    avg_sim_score = sum(sim_scores) / len(sim_scores) if sim_scores else 0
    avg_proc_score = sum(proc_scores) / len(proc_scores) if proc_scores else 0
    
    # Get user distribution
    sim_users = set(a["userId"] for a in simulation_attempts.values())
    proc_users = set(a["userId"] for a in procedure_attempts.values())
    
    return {
        "simulationUsage": {
            "totalAttempts": len(simulation_attempts),
            "completedAttempts": sim_count,
            "uniqueUsers": len(sim_users),
            "averageScore": round(avg_sim_score, 2)
        },
        "procedureUsage": {
            "totalAttempts": len(procedure_attempts),
            "completedAttempts": proc_count,
            "uniqueUsers": len(proc_users),
            "averageScore": round(avg_proc_score, 2)
        },
        "combinedStats": {
            "totalUsers": len(sim_users.union(proc_users)),
            "totalCompleted": sim_count + proc_count,
            "overallEngagement": round(((sim_count + proc_count) / max(1, len(sim_users.union(proc_users)))) * 100, 2)
        }
    }

@app.get("/admin/ai/simulation-metrics")
async def admin_get_simulation_metrics(
    current_user: User = Depends(get_current_user)
):
    """Admin endpoint for simulation performance metrics"""
    if current_user.profession != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    completed_simulations = [a for a in simulation_attempts.values() if a["completed"]]
    
    if not completed_simulations:
        return {"message": "No simulation data available"}
    
    # Calculate various metrics
    scores = [a.get("score", 0) for a in completed_simulations]
    durations = [a.get("durationSeconds", 0) for a in completed_simulations]
    
    return {
        "performanceMetrics": {
            "averageScore": round(sum(scores) / len(scores), 2),
            "medianScore": sorted(scores)[len(scores) // 2],
            "minScore": min(scores),
            "maxScore": max(scores),
            "passRate": round(len([s for s in scores if s >= 70]) / len(scores) * 100, 2),
            "averageDuration": round(sum(durations) / len(durations), 2),
            "averageDecisionsPerSim": round(sum(len(a.get("decisions", [])) for a in completed_simulations) / len(completed_simulations), 2)
        },
        "completionStats": {
            "totalSimulations": len(simulation_attempts),
            "completedSimulations": len(completed_simulations),
            "completionRate": round(len(completed_simulations) / len(simulation_attempts) * 100, 2) if simulation_attempts else 0
        }
    }

@app.get("/admin/ai/procedure-metrics")
async def admin_get_procedure_metrics(
    current_user: User = Depends(get_current_user)
):
    """Admin endpoint for procedure performance metrics"""
    if current_user.profession != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    completed_procedures = [a for a in procedure_attempts.values() if a["completed"]]
    
    if not completed_procedures:
        return {"message": "No procedure data available"}
    
    # Calculate metrics
    scores = [a.get("score", 0) for a in completed_procedures]
    
    competency_levels = {
        "expert": len([a for a in completed_procedures if a.get("score", 0) >= 90]),
        "proficient": len([a for a in completed_procedures if 80 <= a.get("score", 0) < 90]),
        "competent": len([a for a in completed_procedures if 70 <= a.get("score", 0) < 80]),
        "novice": len([a for a in completed_procedures if a.get("score", 0) < 70])
    }
    
    return {
        "performanceMetrics": {
            "averageScore": round(sum(scores) / len(scores), 2),
            "medianScore": sorted(scores)[len(scores) // 2],
            "minScore": min(scores),
            "maxScore": max(scores),
            "competencyDistribution": competency_levels,
            "competencyRate": round((competency_levels["competent"] + competency_levels["proficient"] + competency_levels["expert"]) / len(completed_procedures) * 100, 2)
        },
        "completionStats": {
            "totalProcedures": len(procedure_attempts),
            "completedProcedures": len(completed_procedures),
            "completionRate": round(len(completed_procedures) / len(procedure_attempts) * 100, 2) if procedure_attempts else 0
        }
    }

@app.post("/admin/ai/reset-cache")
async def admin_reset_ai_cache(
    current_user: User = Depends(get_current_user)
):
    """Admin endpoint to reset AI cache (for development)"""
    if current_user.profession != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # In production, this would clear Redis cache
    # For now, just clear in-memory data
    global simulation_attempts, procedure_attempts
    simulation_attempts = {}
    procedure_attempts = {}
    
    return {
        "success": True,
        "message": "AI cache reset successfully",
        "simulationAttemptsCleared": True,
        "procedureAttemptsCleared": True
    }

# =============================================================================
# FRONTEND HELPER ENDPOINTS
# =============================================================================

@app.get("/ai/simulation-specialties")
async def get_simulation_specialties(
    current_user: User = Depends(get_current_active_user)
):
    """Get available specialties for AI simulations"""
    specialties = [
        {"value": "cardiology", "label": "Cardiology"},
        {"value": "emergency", "label": "Emergency Medicine"},
        {"value": "icu", "label": "Intensive Care"},
        {"value": "pediatrics", "label": "Pediatrics"},
        {"value": "obstetrics", "label": "Obstetrics"},
        {"value": "surgery", "label": "Surgery"},
        {"value": "psychiatry", "label": "Psychiatry"},
        {"value": "neurology", "label": "Neurology"}
    ]
    return specialties

@app.get("/ai/procedure-categories")
async def get_procedure_categories(
    current_user: User = Depends(get_current_active_user)
):
    """Get available procedure categories"""
    categories = [
        {"value": "iv_access", "label": "IV Access & Management"},
        {"value": "airway", "label": "Airway Management"},
        {"value": "wound_care", "label": "Wound Care"},
        {"value": "medication", "label": "Medication Administration"},
        {"value": "assessment", "label": "Patient Assessment"},
        {"value": "emergency", "label": "Emergency Procedures"},
        {"value": "diagnostic", "label": "Diagnostic Procedures"},
        {"value": "therapeutic", "label": "Therapeutic Procedures"}
    ]
    return categories

@app.get("/ai/difficulty-levels")
async def get_difficulty_levels(
    current_user: User = Depends(get_current_active_user)
):
    """Get available difficulty levels"""
    levels = [
        {"value": "beginner", "label": "Beginner", "description": "For students and new graduates"},
        {"value": "intermediate", "label": "Intermediate", "description": "For practicing clinicians"},
        {"value": "advanced", "label": "Advanced", "description": "For specialists and experienced practitioners"}
    ]
    return levels




# =============================================================================
# IN-MEMORY STORAGE
# =============================================================================
simulation_attempts = {}
procedure_attempts = {}

# =============================================================================
# AI SIMULATION ENDPOINTS - SIMPLIFIED
# =============================================================================

@app.post("/ai/simulations/generate")
def generate_ai_simulation(
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Generate an EXPERT-level simulation case using OpenAI"""
    import uuid
    from datetime import datetime
    import json
    from openai import OpenAI  # ✅ ADD THIS IMPORT
    
    # Get parameters from frontend
    specialty = data.get("specialty", "emergency")
    difficulty = data.get("difficulty", "expert")
    user_role = data.get("user_role", "nurse")
    scenario_type = data.get("scenario_type", "")
    specialty_context = data.get("specialty_context", "")
    user_id = data.get("user_id", "anonymous")
    
    print(f"🔍 Generating EXPERT simulation for: {specialty}, {user_role}, scenario: {scenario_type}")
    
    try:
        # Get model from .env or use default
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # ✅ Updated default
        
        # ✅ INITIALIZE OPENAI CLIENT
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # ✅ CALL OPENAI WITH CORRECT SYNTAX
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are creating EXPERT-LEVEL clinical simulations for SPECIALISTS.

                    CRITICAL INSTRUCTIONS:
                    1. Create 4 CHALLENGING options - ALL must be clinically plausible
                    2. DO NOT make any option obviously wrong or dangerous
                    3. Focus on NUANCES: timing, sequencing, risk-benefit tradeoffs
                    4. Optimal choice should require EXPERT clinical judgment
                    5. Include: Complex comorbidities, medication interactions, diagnostic uncertainty
                    6. Options should reflect REAL clinical dilemmas experts face
                    7. DO NOT use "isOptimal" in options - assessment happens AFTER selection
                    
                    {specialty_context}
                    
                    Return EXACT JSON format:
                    {{
                        "title": "string (expert-level case title)",
                        "presentation": "string (detailed clinical scenario with complexities)",
                        "demographics": {{
                            "age": "string", 
                            "gender": "string", 
                            "relevantHistory": "string (include comorbidities, medications, social factors)"
                        }},
                        "initialVitals": {{
                            "heartRate": number,
                            "bloodPressure": "string",
                            "temperature": number,
                            "respiratoryRate": number,
                            "oxygenSaturation": number
                        }},
                        "decisionPoints": [
                            {{
                                "situation": "string (complex clinical dilemma)",
                                "options": [
                                    {{"text": "string (expert option 1 - plausible)"}},
                                    {{"text": "string (expert option 2 - plausible)"}},
                                    {{"text": "string (expert option 3 - plausible)"}},
                                    {{"text": "string (expert option 4 - plausible)"}}
                                ],
                                "correctOptionIndex": number // 0-3, which option is optimal (HIDDEN from user)
                            }}
                        ]
                    }}"""
                },
                {
                    "role": "user",
                    "content": f"""Generate an EXPERT-LEVEL clinical simulation for: {user_role}
                    
                    Specialty Category: {specialty}
                    Scenario Type: {scenario_type}
                    Difficulty: EXPERT
                    
                    Make this CHALLENGING for specialists:
                    - Include diagnostic uncertainty
                    - Consider medication interactions
                    - Add ethical considerations
                    - Include resource constraints
                    - All 4 options must be reasonable clinical approaches
                    
                    Example of good expert options for "ICU patient with sepsis":
                    1. Start broad-spectrum antibiotics, fluid resuscitate, obtain cultures, consider source control (optimal)
                    2. Start antibiotics, fluid resuscitate, obtain cultures, wait for response before source control (suboptimal - delay)
                    3. Obtain all cultures first, then start antibiotics, conservative fluids (suboptimal - sequencing)
                    4. Start narrow-spectrum antibiotics based on local epidemiology, aggressive fluids (suboptimal - spectrum)"""
                }
            ],
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        
        # Parse OpenAI response
        content = response.choices[0].message.content
        case_data = json.loads(content)
        
        print(f"✅ OpenAI generated simulation: {case_data.get('title', 'Untitled')}")
        
        # Add metadata to case data
        simulation_id = str(uuid.uuid4())
        case_data["id"] = simulation_id
        case_data["specialty"] = specialty
        case_data["difficulty"] = difficulty
        
        # Create attempt
        attempt_id = str(uuid.uuid4())
        simulation_attempts[attempt_id] = {
            "id": attempt_id,
            "userId": user_id,
            "simulationId": simulation_id,
            "startedAt": datetime.utcnow().isoformat(),
            "decisions": [],
            "completed": False,
            "metadata": {
                "specialty": specialty,
                "difficulty": difficulty,
                "user_role": user_role,
                "scenario_type": scenario_type
            }
        }
        
        return {
            "simulation": case_data,  # ✅ Frontend expects "simulation" not "case"
            "attempt_id": attempt_id   # ✅ Frontend expects "attempt_id" not "attemptId"
        }
        
    except Exception as e:
        print(f"❌ OpenAI generation failed: {str(e)}")
        
        # Fallback: Return a basic simulation
        simulation_id = str(uuid.uuid4())
        attempt_id = str(uuid.uuid4())
        
        fallback_case = {
            "id": simulation_id,
            "title": f"Expert {specialty.title()} Simulation",
            "presentation": f"Complex clinical scenario: {scenario_type}. Requires expert judgment.",
            "demographics": {
                "age": "45",
                "gender": "female",
                "relevantHistory": "Multiple comorbidities requiring careful management"
            },
            "initialVitals": {
                "heartRate": 110,
                "bloodPressure": "150/95",
                "temperature": 38.5,
                "respiratoryRate": 24,
                "oxygenSaturation": 92
            },
            "decisionPoints": [
                {
                    "situation": "Complex clinical presentation requiring expert differential diagnosis and management planning.",
                    "options": [
                        {"text": "Systematic approach: stabilize, diagnose, treat, with continuous reassessment"},
                        {"text": "Focused approach: treat most likely diagnosis while awaiting confirmatory tests"},
                        {"text": "Conservative approach: minimal intervention with close monitoring for deterioration"},
                        {"text": "Aggressive approach: broad-spectrum treatment covering all possibilities"}
                    ],
                    "correctOptionIndex": 0  # First option is optimal
                }
            ],
            "specialty": specialty,
            "difficulty": difficulty
        }
        
        simulation_attempts[attempt_id] = {
            "id": attempt_id,
            "userId": user_id,
            "simulationId": simulation_id,
            "startedAt": datetime.utcnow().isoformat(),
            "decisions": [],
            "completed": False
        }
        
        return {
            "simulation": fallback_case,
            "attempt_id": attempt_id
        }






@app.post("/ai/simulations/start")
def start_simulation(
    data: dict = Body(...)  # REMOVED: current_user: User = Depends(get_current_active_user)
):
    """Start a simulation attempt"""
    import uuid
    from datetime import datetime
    
    simulation_id = data.get("simulation_id")
    user_id = data.get("user_id", "anonymous")  # Get user_id from request
    
    if not simulation_id:
        raise HTTPException(status_code=400, detail="simulation_id required")
    
    attempt_id = str(uuid.uuid4())
    simulation_attempts[attempt_id] = {
        "id": attempt_id,
        "userId": user_id,  # Use user_id from request
        "simulationId": simulation_id,
        "startedAt": datetime.utcnow().isoformat(),
        "decisions": [],
        "completed": False
    }
    
    return {"attemptId": attempt_id}



@app.post("/ai/simulations/decide")
def process_decision(
    data: dict = Body(...)  # REMOVED: current_user: User = Depends(get_current_active_user)
):
    """Process a clinical decision"""
    attempt_id = data.get("attemptId")
    if not attempt_id or attempt_id not in simulation_attempts:
        raise HTTPException(status_code=404, detail="Attempt not found")
    
    # Record decision
    decision = {
        "step": data.get("step", 0),
        "option": data.get("decision", ""),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    simulation_attempts[attempt_id]["decisions"].append(decision)
    
    return {
        "patientResponse": "Patient responds positively to appropriate care.",
        "newVitals": {"hr": 80, "bp": "120/80", "rr": 16, "temp": 37.0, "spo2": 98},
        "complications": [],
        "feedback": "Good clinical decision.",
        "scoreImpact": 10,
        "patientStatus": "stable"
    }

@app.post("/ai/simulations/{attempt_id}/complete")
def complete_simulation(
    attempt_id: str,
    data: dict = Body(...)  # REMOVED: current_user: User = Depends(get_current_active_user)
):
    """Complete a simulation attempt"""
    if attempt_id not in simulation_attempts:
        raise HTTPException(status_code=404, detail="Attempt not found")
    
    simulation_attempts[attempt_id]["completed"] = True
    simulation_attempts[attempt_id]["completedAt"] = datetime.utcnow().isoformat()
    simulation_attempts[attempt_id]["finalScore"] = data.get("score", 0)
    simulation_attempts[attempt_id]["duration"] = data.get("duration", 0)
    
    return {
        "completed": True,
        "final_score": data.get("score", 0),
        "performance_metrics": {
            "decisions_count": len(simulation_attempts[attempt_id]["decisions"]),
            "duration": data.get("duration", 0),
            "efficiency": "good"
        }
    }





@app.post("/ai/simulations/assess")
def assess_simulation_decision(
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    """Assess a user's decision in a simulation using OpenAI"""
    import uuid
    from datetime import datetime
    import json
    
    try:
        # Get parameters from frontend
        attempt_id = data.get("attempt_id")
        simulation_id = data.get("simulation_id")
        step = data.get("step", 0)
        step_title = data.get("step_title", "")
        user_action = data.get("user_action", "")
        is_optimal = data.get("is_optimal", False)
        elapsed_time = data.get("elapsed_time", 0)
        specialty = data.get("specialty", "general")
        user_role = data.get("user_role", "nurse")
        current_vitals = data.get("current_vitals", {})
        current_complications = data.get("current_complications", [])
        available_options = data.get("available_options", [])
        
        print(f"🔍 Assessing decision for attempt: {attempt_id}, step: {step}")
        
        # Get model from .env or use default
        model = os.getenv("OPENAI_MODEL", "gpt-4")
        
        # ✅ CALL OPENAI FOR ASSESSMENT
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are an EXPERT clinical educator providing nuanced feedback for specialists.

                    The user has made a clinical decision. Provide EXPERT-LEVEL feedback.
                    
                    Return EXACT JSON format:
                    {{
                        "new_vitals": {{
                            "heartRate": number,
                            "bloodPressure": "string",
                            "temperature": number,
                            "respiratoryRate": number,
                            "oxygenSaturation": number
                        }},
                        "complications": ["string or empty array"],
                        "clinical_outcome": "string (what happens as result of this decision)",
                        "feedback": "string (nuanced analysis of their choice)",
                        "clinical_reasoning": "string (why this approach is optimal/suboptimal)",
                        "evidence_base": "string (relevant guidelines/trials)",
                        "alternative_perspective": "string (what other experts might consider)",
                        "learning_point": "string (key takeaway for specialists)"
                    }}
                    
                    Be specific, educational, and nuanced. Avoid simplistic "right/wrong" language.
                    
                    Vitals should change realistically based on the decision:
                    - Good decisions: vitals improve or stabilize
                    - Poor decisions: vitals deteriorate
                    - Use realistic ranges for {specialty} patients"""
                },
                {
                    "role": "user",
                    "content": f"""Expert Clinical Decision Assessment
                    
                    Specialty: {specialty}
                    User Role: {user_role}
                    
                    Clinical Situation: {step_title}
                    
                    Available Options Were:
                    {chr(10).join([f"{i+1}. {opt}" for i, opt in enumerate(available_options)])}
                    
                    User Selected: "{user_action}"
                    Was this the optimal choice? {"YES" if is_optimal else "NO"}
                    
                    Current Patient Status:
                    Vitals: {json.dumps(current_vitals)}
                    Complications: {json.dumps(current_complications)}
                    
                    Provide EXPERT feedback:
                    1. If optimal: Explain WHY it's superior, but mention potential pitfalls
                    2. If suboptimal: Explain what makes other approaches better, but acknowledge this choice has merit
                    3. Focus on timing, sequencing, risk stratification
                    4. Reference evidence where applicable
                    5. Include teaching points for specialists
                    
                    Also provide realistic updated vitals based on this decision."""
                }
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # Parse OpenAI response
        content = response.choices[0].message.content
        assessment = json.loads(content)
        
        # Record the decision in the attempt
        if attempt_id in simulation_attempts:
            decision_record = {
                "step": step,
                "action": user_action,
                "is_optimal": is_optimal,
                "timestamp": datetime.utcnow().isoformat(),
                "assessment": assessment
            }
            simulation_attempts[attempt_id]["decisions"].append(decision_record)
        
        print(f"✅ Assessment complete for step {step}")
        
        return assessment
        
    except Exception as e:
        print(f"❌ Assessment failed: {str(e)}")
        
        # Return fallback assessment
        return {
            "new_vitals": current_vitals or {
                "heartRate": 85,
                "bloodPressure": "120/80",
                "temperature": 37.0,
                "respiratoryRate": 18,
                "oxygenSaturation": 97
            },
            "complications": [],
            "clinical_outcome": "Decision processed with basic assessment",
            "feedback": "Basic feedback: " + ("Good clinical decision." if is_optimal else "Consider alternative approaches."),
            "learning_point": "Always consider patient context and available evidence.",
            "evidence_base": "Standard clinical guidelines apply."
        }


# =============================================================================
# PROCEDURE ENDPOINT
# =============================================================================



# Add to your FastAPI app

@app.post("/ai/procedures/generate")
async def generate_procedure(request: dict = Body(...)):
    specialty = request.get("specialty", "emergency")
    difficulty = request.get("difficulty", "advanced")
    
    try:
        # ✅ NEW OPENAI 1.0+ SYNTAX
        from openai import OpenAI
        
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL or "gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical expert creating procedure guides. Return JSON."
                },
                {
                    "role": "user", 
                    "content": f"Create a {difficulty} level procedure for {specialty} with steps, equipment, complications. Return JSON."
                }
            ],
            max_tokens=800,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        # ✅ NEW WAY TO ACCESS RESPONSE
        ai_content = response.choices[0].message.content
        ai_data = json.loads(ai_content)
        
        return {
            "guide": ai_data,
            "attempt_id": f"ai_attempt_{uuid.uuid4().hex[:12]}"
        }
        
    except Exception as e:
        print(f"OpenAI error: {e}")
        # Fallback to mock data
        procedure_guide = {
            "id": f"proc_{uuid.uuid4().hex[:8]}",
            "title": f"{specialty.capitalize()} Procedure Guide",
            "steps": [...],
            "equipment": [...],
            "complications": [...],
            "prerequisites": [...],
            "indications": [...],
            "contraindications": [...]
        }
        return {
            "guide": procedure_guide,
            "attempt_id": f"fallback_{uuid.uuid4().hex[:12]}"
        }


@app.post("/ai/procedures/assess")
async def assess_procedure_step(
    request: dict = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """Assess a procedure step USING OPENAI"""
    try:
        attempt_id = request.get("attempt_id", "")
        step = request.get("step", 0)
        user_action = request.get("user_action", "")
        elapsed_time = request.get("elapsed_time", 0)
        step_title = request.get("step_title", "")
        step_description = request.get("step_description", "")
        is_optimal = request.get("is_optimal", False)
        specialty = request.get("specialty", "general")
        
        # Check if OpenAI is available
        if not OPENAI_AVAILABLE or not config.OPENAI_API_KEY:
            # Fallback to mock
            score = max(0, min(100, 100 - (elapsed_time / 10)))
            return {
                "score": int(score),
                "feedback": f"Good technique. Time: {elapsed_time}s.",
                "correct": score > 70,
                "hints": ["Maintain sterility", "Double-check equipment"]
            }
        
        # ✅ NEW OPENAI 1.0+ SYNTAX
        from openai import OpenAI
        
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL or "gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are an expert medical educator assessing procedural skills.
                    The user is performing: {step_title}
                    
                    Provide detailed feedback on their technique choice.
                    If optimal, explain WHY it's best practice.
                    If suboptimal, explain SPECIFIC dangers and suggest alternatives.
                    
                    Return JSON with exact structure:
                    {{
                        "feedback": "Detailed explanation",
                        "technical_tip": "Specific technique improvement",
                        "safety_note": "Safety consideration",
                        "advanced_consideration": "Expert-level insight",
                        "score_adjustment": -10 to +10,
                        "is_correct": boolean
                    }}"""
                },
                {
                    "role": "user",
                    "content": f"""Step: {step_title}
                    Description: {step_description}
                    User's Action: {user_action}
                    Was this optimal? {is_optimal}
                    Time taken: {elapsed_time} seconds
                    Specialty: {specialty}
                    
                    Provide expert assessment."""
                }
            ],
            max_tokens=config.OPENAI_MAX_TOKENS or 500,
            temperature=config.OPENAI_TEMPERATURE or 0.7,
            response_format={"type": "json_object"}
        )
        
        # ✅ NEW WAY TO ACCESS RESPONSE
        ai_content = response.choices[0].message.content
        assessment_data = json.loads(ai_content)
        
        # Calculate score based on OpenAI assessment
        base_score = 70 if is_optimal else 40
        adjustment = assessment_data.get("score_adjustment", 0)
        final_score = max(0, min(100, base_score + adjustment))
        
        return {
            "score": int(final_score),
            "feedback": assessment_data.get("feedback", "Good technique."),
            "correct": assessment_data.get("is_correct", final_score > 70),
            "hints": [
                assessment_data.get("technical_tip", "Review technique"),
                assessment_data.get("safety_note", "Prioritize safety"),
                assessment_data.get("advanced_consideration", "Consider expert alternatives")
            ],
            "technical_tip": assessment_data.get("technical_tip", ""),
            "safety_note": assessment_data.get("safety_note", ""),
            "advanced_consideration": assessment_data.get("advanced_consideration", "")
        }
        
    except Exception as e:
        print(f"OpenAI assessment error: {e}")
        # Fallback to mock
        score = max(0, min(100, 100 - (elapsed_time / 10)))
        return {
            "score": int(score),
            "feedback": f"Assessment unavailable. Time: {elapsed_time}s.",
            "correct": score > 70,
            "hints": ["Maintain sterility", "Double-check equipment"]
        }


@app.post("/ai/procedures/{attempt_id}/complete")
async def complete_procedure(attempt_id: str, request: dict):
    """Complete a procedure attempt"""
    total_score = request.get("total_score", 0)
    user_actions = request.get("user_actions", [])
    total_time = request.get("total_time", 0)
    
    return {
        "completed": True,
        "final_score": total_score,
        "total_time": total_time,
        "steps_completed": len(user_actions),
        "performance_metrics": {
            "accuracy": total_score / (len(user_actions) * 100) if user_actions else 0,
            "efficiency": total_time / len(user_actions) if user_actions else 0,
            "consistency": "good" if total_score > 70 else "needs_improvement"
        }
    }



@app.post("/ai/procedures/generate-openai")
async def generate_openai_procedure(
    request: dict = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """Call OpenAI from backend (API key in .env)"""
    try:
        # Your .env API key is already loaded in config.OPENAI_API_KEY
        response = await openai_client.chat.completions.create(
    model=config.OPENAI_MODEL,
    messages=[...],  # Your existing prompt
    temperature=0.9,
    response_format={ "type": "json_object" }
)
        
        # Return the OpenAI response
        return JSONResponse(content=json.loads(response.choices[0].message.content))
        
    except Exception as e:
        return {"error": str(e)}



# =============================================================================
# AI AUDITING ENDPOINTS
# =============================================================================


def get_current_admin_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    print("🔍 audit token received:", token)               # <-- add this line
    print("🔍 first user query result:", db.query(User).filter(User.email == "admin@theclamedical.com").first())  # <-- and this
    return db.query(User).filter(User.email == "admin@theclamedical.com").first()


# Add these new routes at the END of your main.py
# They don't interfere with existing routes

@app.post("/audit/check-limit")
def check_daily_limit(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_current_active_user)
):
    user_id = data.get("user_id")
    resource_type = data.get("resource_type")
    
    print(f"🔍 [CHECK-LIMIT] User {user_id} ({current_user.email}) checking {resource_type}")
    
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    today = date.today()
    
    # Calculate CURRENT premium status
    is_currently_premium = (
        current_user.premium_features and
        current_user.premium_features.get('ai_simulation', False) and
        current_user.premium_features.get('procedure_trainer', False)
    )
    
    print(f"🔍 [CHECK-LIMIT] Current premium status: {is_currently_premium}")
    
    # Get or create today's usage record
    usage = db.query(DailyUsageTracking).filter(
        DailyUsageTracking.user_id == user_id,
        DailyUsageTracking.tracking_date == today
    ).first()
    
    if usage:
        print(f"🔍 [CHECK-LIMIT] Found existing usage record (ID: {usage.id})")
        print(f"🔍 [CHECK-LIMIT] Record shows is_premium: {usage.is_premium}")
        print(f"🔍 [CHECK-LIMIT] Current counts - simulations: {usage.simulation_count}")
        
        # CRITICAL: Handle subscription changes during the day
        if usage.is_premium != is_currently_premium:
            print(f"⚠️ [CHECK-LIMIT] Subscription status changed today!")
            print(f"⚠️ [CHECK-LIMIT] Old (record): {usage.is_premium}, New (current): {is_currently_premium}")
            
            # Update the record to reflect current status
            usage.is_premium = is_currently_premium
            
            # Special handling for downgrades: if they used premium resources, 
            # they might exceed basic limits
            if is_currently_premium:
                print(f"🎉 [CHECK-LIMIT] User UPGRADED to premium!")
            else:
                print(f"⚠️ [CHECK-LIMIT] User DOWNGRADED to basic!")
                # Note: They keep their current usage count, 
                # but will be blocked if they exceed basic limits
            
            db.commit()
    else:
        print(f"🔍 [CHECK-LIMIT] Creating new usage record")
        usage = DailyUsageTracking(
            user_id=user_id,
            tracking_date=today,
            is_premium=is_currently_premium,
            simulation_count=0,           # ← FIXED
            procedure_count=0,            # ← FIXED  
            ai_quiz_questions_count=0     # ← FIXED
        )
        db.add(usage)
        db.commit()
    
    FIELD_MAPPING = {
        'simulation': 'simulation_count',
        'procedure': 'procedure_count',
        'quiz_question': 'ai_quiz_questions_count'
    }
    
    count_field = FIELD_MAPPING.get(resource_type)
    if not count_field:
        raise HTTPException(status_code=400, detail=f"Unknown resource type: {resource_type}")
    
    current_count = getattr(usage, count_field, 0)
       
    # ========== CUSTOM LIMITS OVERRIDE EVERYTHING ==========
    custom_limits = current_user.premium_features.get('custom_limits', {}) if current_user.premium_features else {}
    
    # Get custom limit for this resource type
    limit = None
    if resource_type == 'simulation':
        limit = custom_limits.get('simulations_per_day')
    elif resource_type == 'procedure':
        limit = custom_limits.get('procedures_per_day')
    elif resource_type == 'quiz_question':
        limit = custom_limits.get('quiz_questions_per_day')
    
    # Determine limit type
    if limit is not None:
        limit_type = "CUSTOM"
        print(f"🔍 [CHECK-LIMIT] Using CUSTOM limit: {limit}")
    else:
        # NO CUSTOM LIMITS → Use defaults based on user tier
        if is_currently_premium:
            # PREMIUM defaults: 5 simulations, 5 procedures, 75 quiz questions
            DEFAULT_LIMITS = {'simulation': 5, 'procedure': 5, 'quiz_question': 75}
            limit_type = "PREMIUM_DEFAULT"
            print(f"🔍 [CHECK-LIMIT] Premium user → Default limits: 5/5/75")
        else:
            # BASIC defaults: 1 simulation, 1 procedure, 15 quiz questions
            DEFAULT_LIMITS = {'simulation': 1, 'procedure': 1, 'quiz_question': 15}
            limit_type = "BASIC_DEFAULT"
            print(f"🔍 [CHECK-LIMIT] Basic user → Default limits: 1/1/15")
        
        limit = DEFAULT_LIMITS.get(resource_type)
    # ========== END CUSTOM LIMITS LOGIC ==========
    
    print(f"🔍 [CHECK-LIMIT] Applying {limit_type} limits: {current_count}/{limit if limit is not None else 'unlimited'}")
    
    # Make decision
    if limit is None:
        allowed = True
        reason = "no_limit_defined"
        print(f"✅ [CHECK-LIMIT] Decision: No limit defined → Allowed")
    else:
        allowed = current_count < limit
        reason = "within_limit" if allowed else "limit_exceeded"
        
        # Special messages for edge cases
        if not allowed and not is_currently_premium and current_count >= 1:
            # Basic user who used their 1 allocation
            print(f"🚫 [CHECK-LIMIT] Basic user used their 1 {resource_type} allocation")
        elif not allowed and is_currently_premium and current_count >= limit:
            # Premium user who used their allocations
            print(f"🚫 [CHECK-LIMIT] Premium user used their {limit} {resource_type} allocations")
        else:
            print(f"✅ [CHECK-LIMIT] {limit_type} user → Allowed: {allowed} ({current_count}/{limit})")
    
    # Record the decision for audit
    decision = RateLimitDecision(
        user_id=user_id,
        decision_time=datetime.utcnow(),
        resource_type=resource_type,
        allowed=allowed,
        reason=reason,
        current_count=current_count,
        limit_value=limit,
    )
    db.add(decision)
    db.commit()
    
    return {
        "allowed": allowed,
        "reason": reason,
        "current": current_count,
        "limit": limit,
        "is_premium": is_currently_premium,  # Return CURRENT status
        "limit_type": limit_type
    }









@app.post("/audit/record-usage")
def record_daily_usage(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    #current_user: User = Depends(get_current_active_user)
):
    """
    Record usage AFTER successful generation.
    """
    
    user_id = current_user.id
    resource_type = data.get("resource_type")
    count = data.get("count", 1)
   
    
   # if current_user.id != user_id:
       # raise HTTPException(status_code=403, detail="Not authorized")
    
    today = date.today()
    
    # Get today's record
    usage = db.query(DailyUsageTracking).filter(
        DailyUsageTracking.user_id == user_id,
        DailyUsageTracking.tracking_date == today
    ).first()

        
    if not usage:
        raise HTTPException(status_code=400, detail="No daily record found. Call check-limit first.")
           
    # Field mapping for correct column names
    FIELD_MAPPING = {
        'simulation': 'simulations',
        'procedure': 'procedures',
        'quiz_question': 'quiz_questions'
    }
    
    count_field = FIELD_MAPPING.get(resource_type)
    if not count_field:
        raise HTTPException(status_code=400, detail=f"Unknown resource type: {resource_type}")
      
    
    # Increment counter
    current_value = getattr(usage, count_field, 0)
    setattr(usage, count_field, current_value + count)
    usage.updated_at = datetime.utcnow()

    
    db.commit()
       
    return {
        "success": True,
        "resource_type": resource_type,
        "new_count": getattr(usage, count_field),
        "date": str(today)
    }


@app.get("/audit/user-usage/{user_id}")
def get_user_daily_usage(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get user's current usage for frontend display.
    """
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    today = date.today()
    
    usage = db.query(DailyUsageTracking).filter(
        DailyUsageTracking.user_id == user_id,
        DailyUsageTracking.tracking_date == today
    ).first()
    
    if not usage:
        # Return zeros if no record yet
        
        # ========== UPDATED LOGIC ==========
        custom_limits = current_user.premium_features.get('custom_limits', {}) if current_user.premium_features else {}
        
        # Get premium status
        is_premium = current_user.premium_features and current_user.premium_features.get('ai_simulation', False) and current_user.premium_features.get('procedure_trainer', False)
        
        # Get custom limits if they exist
        sim_limit = custom_limits.get('simulations_per_day')
        proc_limit = custom_limits.get('procedures_per_day')
        quiz_limit = custom_limits.get('quiz_questions_per_day')
        
        # If no custom limits, use tier defaults
        if sim_limit is None:
            sim_limit = 5 if is_premium else 1  # Premium: 5, Basic: 1
        if proc_limit is None:
            proc_limit = 5 if is_premium else 1  # Premium: 5, Basic: 1
        if quiz_limit is None:
            quiz_limit = 75 if is_premium else 15  # Premium: 75, Basic: 15
        
        limits = {
            "simulations": sim_limit,
            "procedures": proc_limit,
            "ai_quiz_questions": quiz_limit
        }
        # ========== END UPDATED LOGIC ==========
        
        return {
            "user_id": user_id,
            "date": str(today),
            "is_premium": is_premium,
            "usage": {
                "simulations": {"count": 0, "limit": limits["simulations"]},
                "procedures": {"count": 0, "limit": limits["procedures"]},
                "ai_quiz_questions": {"count": 0, "limit": limits["ai_quiz_questions"]}
            }
        }
    
    # ========== UPDATED LOGIC ==========
    custom_limits = current_user.premium_features.get('custom_limits', {}) if current_user.premium_features else {}
    
    # Get custom limits if they exist
    sim_limit = custom_limits.get('simulations_per_day')
    proc_limit = custom_limits.get('procedures_per_day')
    quiz_limit = custom_limits.get('quiz_questions_per_day')
    
    # If no custom limits, use tier defaults
    if sim_limit is None:
        sim_limit = 5 if usage.is_premium else 1  # Premium: 5, Basic: 1
    if proc_limit is None:
        proc_limit = 5 if usage.is_premium else 1  # Premium: 5, Basic: 1
    if quiz_limit is None:
        quiz_limit = 75 if usage.is_premium else 15  # Premium: 75, Basic: 15
    
    limits = {
        "simulations": sim_limit,
        "procedures": proc_limit,
        "ai_quiz_questions": quiz_limit
    }
    # ========== END UPDATED LOGIC ==========
    
    return {
        "user_id": user_id,
        "date": str(today),
        "is_premium": usage.is_premium,
        "usage": {
            "simulations": {
                "count": usage.simulation_count,
                "limit": limits["simulations"]
            },
            "procedures": {
                "count": usage.procedure_count,
                "limit": limits["procedures"]
            },
            "ai_quiz_questions": {
                "count": usage.ai_quiz_questions_count,
                "limit": limits["ai_quiz_questions"]
            }
        }
    }







# ========== ADMIN AUDIT ENDPOINTS ONLY ==========

def is_user_admin(user: User) -> bool:
    """Check if user has admin privileges - ADJUST THIS BASED ON YOUR USER MODEL"""
    # Example: Check if user has admin role or specific email
    if hasattr(user, 'role') and user.role == 'admin':
        return True
    if hasattr(user, 'is_admin') and user.is_admin == True:
        return True
    # Add other admin checks based on your User model
    return False

def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    """Verify user is admin"""
    if not is_user_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# 1. DAILY USAGE SUMMARY (Admin only)



@app.get("/admin/audit/daily-usage/{date}")
def get_daily_usage_summary(
    date: str,
    db: Session = Depends(get_db),
    #admin_user: User = Depends(get_current_admin_user)  # UNCOMMENTED: Admin check
):
    """Get daily usage summary for all users (ADMIN ONLY)"""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Get all usage for the date
    usage_records = db.query(DailyUsageTracking).filter(
        DailyUsageTracking.tracking_date == query_date
    ).all()
    
    # Calculate totals - CORRECTED COLUMN NAMES
    total_simulations = sum(u.simulation_count for u in usage_records)                
    total_procedures = sum(u.procedure_count for u in usage_records)  # FIXED: procedure_count
    total_quiz_questions = sum(u.ai_quiz_questions_count for u in usage_records)  # FIXED: ai_quiz_questions_count
    premium_users = sum(1 for u in usage_records if u.is_premium)
    
    return {
        "date": str(query_date),
        "total_users": len(usage_records),
        "total_simulations": total_simulations,
        "total_procedures": total_procedures,
        "total_quiz_questions": total_quiz_questions,
        "premium_users": premium_users,
        "basic_users": len(usage_records) - premium_users,
    }

# 2. USER USAGE LIST (Admin only)
@app.get("/admin/audit/user-usage")
def get_user_usage_list(
    date: str = Query(default_factory=lambda: date.today().isoformat()),
    db: Session = Depends(get_db),
    #admin_user: User = Depends(get_current_admin_user)  # UNCOMMENTED: Admin check
):
    """Get usage list for all users on specific date (ADMIN ONLY)"""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Get usage records with user info
    usage_records = db.query(
        DailyUsageTracking,
        User.email,
        User.full_name
    ).outerjoin(
        User, DailyUsageTracking.user_id == User.id
    ).filter(
        DailyUsageTracking.tracking_date == query_date
    ).all()
    
    result = []
    for usage, email, name in usage_records:
        result.append({
            "user_id": usage.user_id,
            "email": email or f"User_{usage.user_id}",
            "name": name or f"User {usage.user_id}",  # FIXED: removed undefined 'full_name'
            "is_premium": usage.is_premium,
            "simulations": usage.simulation_count,  # FIXED: simulation_count
            "procedures": usage.procedure_count,    # FIXED: procedure_count
            "ai_quiz_questions": usage.ai_quiz_questions_count,  # FIXED: ai_quiz_questions_count
            "date": str(usage.tracking_date)
        })
    
    return result







# 3. RATE LIMIT DECISIONS (Admin only)
@app.get("/admin/audit/rate-decisions")
def get_rate_limit_decisions(
    date: str = Query(default_factory=lambda: date.today().isoformat()),
    limit: int = Query(50, ge=1, le=1000),
    resource_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    #admin_user: User = Depends(get_current_admin_user)  # Admin check
):
    """Get rate limit decisions for monitoring (ADMIN ONLY)"""
    try:
        query_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Build query
    query = db.query(
        RateLimitDecision,
        User.email,
        User.name
    ).outerjoin(
        User, RateLimitDecision.user_id == User.id
    ).filter(
        func.date(RateLimitDecision.decision_time) == query_date
    )
    
    # Apply resource type filter if provided
    if resource_type and resource_type != 'all':
        query = query.filter(RateLimitDecision.resource_type == resource_type)
    
    # Get results
    decisions = query.order_by(
        RateLimitDecision.decision_time.desc()
    ).limit(limit).all()
    
    result = []
    for decision, email, name in decisions:
        result.append({
            "id": decision.id,
            "user_id": decision.user_id,
            "decision_time": decision.decision_time.isoformat(),
            "resource_type": decision.resource_type,
            "allowed": decision.allowed,
            "reason": decision.reason,
            "current_count": decision.current_count,
            "limit_value": decision.limit_value,
            "user_name": name or f"User {decision.user_id}",
            "user_email": email or f"user_{decision.user_id}@example.com"
        })
    
    return result

# 4. RESET USER USAGE (Admin only)
@app.post("/admin/audit/reset-usage/{user_id}")
def reset_user_daily_usage(
    user_id: int,
    db: Session = Depends(get_db),
    #admin_user: User = Depends(get_current_admin_user)  # Admin check
):
    """Reset user's daily usage counters (ADMIN ONLY)"""
    today = date.today()
    
    # Get today's usage record
    usage = db.query(DailyUsageTracking).filter(
        DailyUsageTracking.user_id == user_id,
        DailyUsageTracking.tracking_date == today
    ).first()
    
    if usage:
        # Reset all counters
        usage.simulation_count = 0
        usage.procedure_count = 0
        usage.ai_quiz_questions_count = 0
        usage.updated_at = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "message": f"Daily usage reset for user {user_id}",
            "date": str(today)
        }
    else:
        # No usage record exists yet for today
        return {
            "success": True,
            "message": f"No usage recorded today for user {user_id}",
            "date": str(today)
        }




# in-memory config (persist in DB/Redis if you want)
# System-wide default limits by tier (use this in BOTH endpoints)
TIER_LIMITS = {
    "premium": {"simulation": 5, "procedure": 5, "quiz_question": 75},
    "basic": {"simulation": 1, "procedure": 1, "quiz_question": 15}
}

# 1. GET system limits (admin dashboard)
@app.get("/admin/audit/limits")
def get_limits(_: User = Depends(get_current_admin_user)):
    return TIER_LIMITS

# 2. UPDATE system limits (admin can change defaults)
@app.patch("/admin/audit/limits")
def update_limits(body: dict, _: User = Depends(get_current_admin_user)):
    if "premium" in body:
        TIER_LIMITS["premium"].update(body["premium"])
    if "basic" in body:
        TIER_LIMITS["basic"].update(body["basic"])
    return {"success": True, "new_limits": TIER_LIMITS}

# 3. GET specific user's daily usage (admin monitoring)
@app.get("/admin/audit/user-usage/{user_id}")
def get_single_user_usage(
    user_id: int,
    date: dtdate = Query(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin_user)
):
    usage = db.query(DailyUsageTracking).filter_by(user_id=user_id, tracking_date=date).first()
    if not usage:
        return {"user_id": user_id, "date": str(date), "is_premium": False, "simulations": 0, "procedures": 0, "ai_quiz_questions": 0}
    return {
        "user_id": user_id,
        "date": str(date),
        "is_premium": usage.is_premium,
        "simulations": usage.simulation_count,
        "procedures": usage.procedure_count,
        "ai_quiz_questions": usage.ai_quiz_questions_count
    }



@app.post("/create-admin")
def create_admin_user(
    email: str = "admin@thecla.com",
    password: str = "admin123",
    db: Session = Depends(get_db)
):
    """TEMPORARY: Create admin user (remove after use)"""
    try:
        from passlib.context import CryptContext
        
        # Initialize password hasher
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            # Update to admin using CORRECT field names
            existing_user.is_admin = True
            existing_user.role = "admin"
            existing_user.status = "active"
            db.commit()
            return {
                "success": True,
                "message": f"User {email} updated to admin",
                "user_id": existing_user.id
            }
        
        # Create new admin user with CORRECT field names
        hashed_password = pwd_context.hash(password)
        
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name="Admin User",  # CORRECT: full_name not name
            phone="+1234567890",
            profession="admin",
            specialist_type="admin",
            status="active",  # CORRECT: status not is_active
            created_at=datetime.utcnow(),
            approved_at=datetime.utcnow(),
            is_admin=True,  # NEW FIELD
            role="admin",   # NEW FIELD
            premium_features={
                "ai_simulation": True,
                "procedure_trainer": True,
                "ai_job_match": True,
                "usmle": True
            }
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"✅ Admin user created: {email} (ID: {user.id})")
        
        return {
            "success": True,
            "message": f"Admin user {email} created",
            "user_id": user.id,
            "email": email,
            "password": password  # Only for initial setup
        }
        
    except Exception as e:
        print(f"❌ Failed to create admin: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create admin: {str(e)}")


























if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)