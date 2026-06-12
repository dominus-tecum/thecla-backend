import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
import sqlite3

# Use DATABASE_URL from environment (PostgreSQL on Render, SQLite locally)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./theclamed.db")

# Create engine - NO conditions, NO check_same_thread
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Keamed database (stays SQLite)
KEAMED_DATABASE_URL = "sqlite:///./keamed.db"
keamed_engine = create_engine(KEAMED_DATABASE_URL, connect_args={"check_same_thread": False})
KeamedSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=keamed_engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def init_keamed_db():
    conn = sqlite3.connect('keamed.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keamed_exams (
            id TEXT PRIMARY KEY,
            title TEXT,
            discipline_id TEXT,
            exam_type TEXT,
            is_active BOOLEAN DEFAULT FALSE,
            time_per_question INTEGER DEFAULT 1,
            total_questions INTEGER DEFAULT 10
        )
    ''')
    cursor.execute('''  
        CREATE TABLE IF NOT EXISTS keamed_questions (
            id TEXT PRIMARY KEY,
            exam_id TEXT,
            question_text TEXT,
            options TEXT,
            correct_answer TEXT,
            FOREIGN KEY (exam_id) REFERENCES keamed_exams(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keamed_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            user_name TEXT,
            user_profession TEXT,
            exam_type TEXT,
            exam_id TEXT,
            exam_title TEXT,
            score INTEGER,
            total_questions INTEGER,
            time_spent INTEGER,
            user_answers TEXT,
            topic_performance TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS keamed_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT,
            config_value TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Keamed tables created successfully")

def get_keamed_db():
    db = KeamedSessionLocal()
    try:
        yield db
    finally:
        db.close()