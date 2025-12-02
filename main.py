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

# ✅ ADD SECURITY IMPORTS
from jose import JWTError, jwt
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# NEW IMPORTS FOR STUDY NOTES
import requests
from bs4 import BeautifulSoup

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

# ✅ TOKEN RESPONSE MODEL
class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    full_name: str
    profession: str
    email: str

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

# ✅ SECURE LOGIN ENDPOINT WITH JWT
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
        "email": user.email
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




# DELETE SPECIfic EXAM

@app.delete("/admin/exams/{exam_id}")
def delete_singular_exam(
    exam_id: str,
    db: Session = Depends(get_db)
):
    """Delete a exam (singular exam)"""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Study note not found")
    
    db.delete(exam)
    db.commit()
    
    return {"msg": f"exam'{exam.title}' deleted successfully"}


@app.delete("/admin/exams/discipline/{discipline}")
def delete_exams_by_discipline(
    discipline: str,
    db: Session = Depends(get_db)
):
    """Delete all exams (plural exams) for a specific discipline"""
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
        "msg": f"Deleted {deleted_count} exams for discipline: {discipline}",
        "deleted_count": deleted_count,
        "discipline": discipline
    }





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

# ✅ SECURED EXAM ENDPOINTS WITH JWT AUTH






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
            is_released=True  # Auto-release study materials
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
            "msg": "Singular exam created successfully",
            "exam_id": exam_id,
            "questions_count": len(questions_data)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating exam: {str(e)}")




@app.delete("/exam/{exam_id}")
def delete_exam_singular(
    exam_id: str,
    db: Session = Depends(get_db)
):
    """Delete a specific study note"""
    try:
        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise HTTPException(status_code=404, detail="Note not found")
        
        # Delete related questions first
        db.query(Question).filter(Question.exam_id == exam_id).delete()
        
        # Delete the exam
        db.delete(exam)
        db.commit()
        
        return {"msg": f"Note {exam_id} deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting note: {str(e)}")



@app.delete("/exam/discipline/{discipline}")
def delete_exams_by_discipline(
    discipline: str,
    db: Session = Depends(get_db)
):
    """Delete all study notes in a discipline"""
    try:
        # Find all exams for this discipline
        exams = db.query(Exam).filter(
            Exam.discipline_id == discipline,
            Exam.source == "singular"
        ).all()
        
        if not exams:
            return {"msg": f"No notes found for discipline {discipline}"}
        
        exam_ids = [exam.id for exam in exams]
        
        # Delete related questions
        db.query(Question).filter(Question.exam_id.in_(exam_ids)).delete()
        
        # Delete exams
        db.query(Exam).filter(Exam.id.in_(exam_ids)).delete()
        db.commit()
        
        return {"msg": f"Deleted {len(exams)} notes for discipline {discipline}"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting notes: {str(e)}")


# =============================================================================
# STUDY NOTES ENDPOINTS ENDS HERE
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
            "approved_at": user.approved_at
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
            "completed_at": activity.timestamp
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









if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)