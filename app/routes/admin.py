from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.models import ExamResult
from app.database import SessionLocal
from app.routes.auth import get_current_user
from pydantic import BaseModel
from typing import List

router = APIRouter()

class ExamResultRead(BaseModel):
    id: str
    user_id: str
    exam_id: str
    score: int
    taken_at: str

    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def is_admin(user):
    # Dummy: consider discipline_id "admin" as admin
    return user.discipline_id == "admin"

@router.get("/history", response_model=List[ExamResultRead])
def get_exam_history(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not is_admin(user):
        return []
    results = db.query(ExamResult).all()
    return results