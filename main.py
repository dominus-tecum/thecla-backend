from fastapi import FastAPI, Depends, HTTPException, Body, Query, Request, status
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, create_engine, Boolean, Text, Enum, func
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from sqlalchemy.sql import case
from passlib.context import CryptContext
from datetime import datetime
import uvicorn
from typing import Optional
import hashlib
import secrets
import re  # ADDED: For rationale parsing
import phonenumbers  # ADDED: For phone number validation
from enum import Enum as PyEnum
import uuid  # ADDED: For generating UUIDs

# ✅ ADD SECURITY IMPORTS
from jose import JWTError, jwt
from datetime import timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

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

class Question(Base):
    __tablename__ = "questions"
    id = Column(String, primary_key=True, index=True)
    exam_id = Column(String, ForeignKey("exams.id"))
    text = Column(String)
    options = Column(JSON)
    correct_idx = Column(Integer)
    rationale = Column(Text, nullable=True)  # NEW: Added rationale column
    exam = relationship("Exam", back_populates="questions")

# DROP AND RECREATE TABLES TO ADD NEW COLUMNS
# Base.metadata.drop_all(bind=engine)  # THIS WILL RESET YOUR DATABASE
Base.metadata.create_all(bind=engine)

# UTILS

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

# NEW: ADMIN USER MANAGEMENT ENDPOINTS

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

# UPDATED EXAM ENDPOINTS WITH DYNAMIC DISCIPLINE SYSTEM

# NEW: ADD MISSING POST ENDPOINTS FOR EXAMS
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

# OTHER ENDPOINTS (UPDATED WITH STATUS CHECK)

@app.get("/notes/{note_id}")
def view_note(
    note_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    log_activity(db, current_user.id, "view_note", {"note_id": note_id})
    return {"msg": "Note viewed", "note_id": note_id}

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

# ADMIN ENDPOINTS

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

# =============================================================================
# NEW ADMIN ENDPOINTS - ADDED FOR COMPLETE ADMIN FUNCTIONALITY
# =============================================================================

# NEW: Exam submission endpoint
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
            raise HTTPException(status_code=404, detail="Exam not found")
        
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

# Run the application
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)