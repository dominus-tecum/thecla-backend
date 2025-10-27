from fastapi import APIRouter, Depends, HTTPException, status, Request
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from app.models import User
from app.database import SessionLocal
import uuid
import os

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Use a secure random secret key for production!
SECRET_KEY = os.environ.get("SECRET_KEY", "your_super_secure_secret_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    discipline_id: str

class UserRead(BaseModel):
    id: str
    email: str
    name: str
    discipline_id: str
    created_at: datetime

    class Config:
        orm_mode = True

class LoginRequest(BaseModel):
    email: str
    password: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    # bcrypt supports passwords up to 72 bytes
    if len(password.encode('utf-8')) > 72:
        raise ValueError("Password cannot be longer than 72 bytes")
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user(email: str, db: Session):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(email: str, password: str, db: Session):
    user = get_user(email, db)
    if not user or not verify_password(password, user.password_hash):
        return None
    return user

def get_token_from_header(request: Request):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ")[1]
    return None

def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = get_token_from_header(request)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = get_user(token_data.email, db)
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user(user.email, db)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(user.password.encode('utf-8')) > 72:
        raise HTTPException(status_code=400, detail="Password too long. Must be 72 bytes or less.")
    try:
        hashed_pw = get_password_hash(user.password)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    new_user = User(
        id=str(uuid.uuid4()),
        email=user.email,
        password_hash=hashed_pw,
        name=user.name,
        discipline_id=user.discipline_id,
        created_at=datetime.utcnow(),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=Token)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(request.email, request.password, db)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/reauth")
def reauth(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(request.email, request.password, db)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    return {"success": True, "user": user}