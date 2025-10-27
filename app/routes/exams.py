from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.models import Exam, Question, ExamResult
from app.database import SessionLocal
from app.routes.auth import get_current_user
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid

router = APIRouter()

class QuestionCreate(BaseModel):
    text: str
    options: list
    correct_idx: int

class ExamCreate(BaseModel):
    title: str
    discipline_id: str
    time_limit: int
    questions: List[QuestionCreate]

class ExamRead(BaseModel):
    id: str
    title: str
    discipline_id: str
    time_limit: int

    class Config:
        orm_mode = True

class QuestionRead(BaseModel):
    id: str
    text: str
    options: list
    correct_idx: int

    class Config:
        orm_mode = True

class ExamDetailRead(BaseModel):
    id: str
    title: str
    discipline_id: str
    time_limit: int
    questions: List[QuestionRead]

    class Config:
        orm_mode = True

class SubmitExamRequest(BaseModel):
    exam_id: str
    answers: List[int]

class ExamResultRead(BaseModel):
    id: str
    user_id: str
    exam_id: str
    score: int
    taken_at: datetime

    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[ExamRead])
def list_exams(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    exams = db.query(Exam).filter(Exam.discipline_id == user.discipline_id).all()
    return exams

@router.post("/", response_model=ExamRead)
def create_exam(exam: ExamCreate, request: Request, db: Session = Depends(get_db)):
    new_exam = Exam(
        id=str(uuid.uuid4()),
        title=exam.title,
        discipline_id=exam.discipline_id,
        time_limit=exam.time_limit,
    )
    db.add(new_exam)
    db.commit()
    db.refresh(new_exam)
    for q in exam.questions:
        new_question = Question(
            id=str(uuid.uuid4()),
            exam_id=new_exam.id,
            text=q.text,
            options=q.options,
            correct_idx=q.correct_idx,
        )
        db.add(new_question)
    db.commit()
    return new_exam

@router.get("/{exam_id}", response_model=ExamDetailRead)
def get_exam(exam_id: str, db: Session = Depends(get_db)):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    questions = db.query(Question).filter(Question.exam_id == exam.id).all()
    return {
        "id": exam.id,
        "title": exam.title,
        "discipline_id": exam.discipline_id,
        "time_limit": exam.time_limit,
        "questions": questions
    }

@router.delete("/{exam_id}")
def delete_exam(exam_id: str, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db_exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not db_exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    db.delete(db_exam)
    db.commit()
    return {"success": True}

@router.post("/submit", response_model=ExamResultRead)
def submit_exam(request_data: SubmitExamRequest, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    exam = db.query(Exam).filter(Exam.id == request_data.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    questions = db.query(Question).filter(Question.exam_id == exam.id).all()
    if len(questions) != len(request_data.answers):
        raise HTTPException(status_code=400, detail="Number of answers does not match number of questions")
    score = sum(
        1 for idx, q in enumerate(questions)
        if request_data.answers[idx] == q.correct_idx
    )
    result = ExamResult(
        id=str(uuid.uuid4()),
        user_id=user.id,
        exam_id=exam.id,
        score=score,
        taken_at=datetime.utcnow()
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result

@router.get("/results", response_model=List[ExamResultRead])
def list_user_results(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    results = db.query(ExamResult).filter(ExamResult.user_id == user.id).all()
    return results