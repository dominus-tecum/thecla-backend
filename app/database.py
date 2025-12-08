from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base
import sqlite3  # ADD THIS AT THE TOP OF THE FILE

# Original database for other features
SQLALCHEMY_DATABASE_URL = "sqlite:///./theclamed.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# NEW: Keamed database for exams
KEAMED_DATABASE_URL = "sqlite:///./keamed.db"
keamed_engine = create_engine(KEAMED_DATABASE_URL, connect_args={"check_same_thread": False})
KeamedSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=keamed_engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def init_keamed_db():
    """Create the Keamed-specific tables"""
    conn = sqlite3.connect('keamed.db')
    cursor = conn.cursor()
    
    # Create keamed_exams table
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
    
    # Create keamed_questions table  
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
    
    # Create keamed_results table
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
    
    # Create keamed_config table
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

# NEW: Keamed database dependency
def get_keamed_db():
    db = KeamedSessionLocal()
    try:
        yield db
    finally:
        db.close()