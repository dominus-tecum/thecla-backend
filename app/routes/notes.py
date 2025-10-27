from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session
from app.models import StudyNote
from app.database import SessionLocal
from app.routes.auth import get_current_user
from pydantic import BaseModel
from typing import List
from datetime import datetime
import uuid
import os

router = APIRouter()

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class StudyNoteCreate(BaseModel):
    title: str
    discipline_id: str
    access_start: datetime
    access_end: datetime

class StudyNoteUpdate(BaseModel):
    title: str
    access_start: datetime
    access_end: datetime

class StudyNoteRead(BaseModel):
    id: str
    title: str
    file_url: str
    discipline_id: str
    access_start: datetime
    access_end: datetime

    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[StudyNoteRead])
def list_notes(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    notes = db.query(StudyNote).filter(StudyNote.discipline_id == user.discipline_id).all()
    return notes

@router.post("/", response_model=StudyNoteRead)
def create_note(note: StudyNoteCreate, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    new_note = StudyNote(
        id=str(uuid.uuid4()),
        title=note.title,
        file_url="",
        discipline_id=note.discipline_id,
        access_start=note.access_start,
        access_end=note.access_end,
        user_id=user.id
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note

@router.put("/{note_id}", response_model=StudyNoteRead)
def update_note(note_id: str, note: StudyNoteUpdate, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db_note = db.query(StudyNote).filter(StudyNote.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    db_note.title = note.title
    db_note.access_start = note.access_start
    db_note.access_end = note.access_end
    db.commit()
    db.refresh(db_note)
    return db_note

@router.delete("/{note_id}")
def delete_note(note_id: str, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    db_note = db.query(StudyNote).filter(StudyNote.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(db_note)
    db.commit()
    return {"success": True}

@router.post("/upload/{note_id}")
def upload_note_file(note_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    db_note = db.query(StudyNote).filter(StudyNote.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    file_location = os.path.join(UPLOAD_DIR, f"{note_id}_{file.filename}")
    with open(file_location, "wb") as buffer:
        buffer.write(file.file.read())
    db_note.file_url = file_location
    db.commit()
    db.refresh(db_note)
    return {"success": True, "file_url": file_location}