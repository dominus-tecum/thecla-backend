import sqlite3
from sqlite3 import Error
import requests
import os

def check_database():
    """Check what's actually in the database"""
    
    db_path = 'theclamed.db'
    print(f"🔍 Checking database: {db_path}")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📊 CHECKING DATABASE STRUCTURE:")
        
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Found tables: {[table[0] for table in tables]}")
        
        # Check if exams and questions tables exist
        if 'exams' in [table[0] for table in tables]:
            print("\n✅ Exams table exists")
            # Check exams columns
            cursor.execute("PRAGMA table_info(exams)")
            exam_columns = cursor.fetchall()
            print("Exams table columns:")
            for col in exam_columns:
                print(f"  - {col[1]} ({col[2]})")
        
        if 'questions' in [table[0] for table in tables]:
            print("\n✅ Questions table exists")
            # Check questions columns
            cursor.execute("PRAGMA table_info(questions)")
            question_columns = cursor.fetchall()
            print("Questions table columns:")
            for col in question_columns:
                print(f"  - {col[1]} ({col[2]})")
        
        # Now check the actual data
        print("\n📊 EXAMS TABLE DATA:")
        cursor.execute("SELECT id, title, discipline_id, source FROM exams WHERE source = 'quiz'")
        exams = cursor.fetchall()
        print(f"Found {len(exams)} QUIZ exams:")
        for exam in exams:
            print(f"  - {exam[0]}: {exam[1]} (Discipline: {exam[2]}, Source: {exam[3]})")
        
        # Check all exams to see what's there
        cursor.execute("SELECT id, title, discipline_id, source FROM exams LIMIT 10")
        all_exams = cursor.fetchall()
        print(f"\n📋 ALL EXAMS (first 10):")
        for exam in all_exams:
            print(f"  - {exam[0]}: {exam[1]} (Discipline: {exam[2]}, Source: {exam[3]})")
        
        print(f"\n❓ QUESTIONS TABLE DATA:")
        cursor.execute("SELECT exam_id, COUNT(*) as count FROM questions GROUP BY exam_id")
        question_counts = cursor.fetchall()
        print("Questions per exam:")
        for exam_id, count in question_counts:
            print(f"  - {exam_id}: {count} questions")
        
        # Check if any questions have topics (CRITICAL FOR SMART QUIZ)
        cursor.execute("SELECT COUNT(*) FROM questions WHERE topic IS NOT NULL AND topic != ''")
        questions_with_topics = cursor.fetchone()[0]
        print(f"\n🎯 Questions with topics: {questions_with_topics}")
        
        # Check questions without topics (PROBLEM!)
        cursor.execute("SELECT COUNT(*) FROM questions WHERE topic IS NULL OR topic = ''")
        questions_without_topics = cursor.fetchone()[0]
        print(f"❌ Questions WITHOUT topics: {questions_without_topics}")
        
        # Show sample questions with topics
        if questions_with_topics > 0:
            cursor.execute("SELECT exam_id, text, topic FROM questions WHERE topic IS NOT NULL LIMIT 5")
            sample_questions = cursor.fetchall()
            print("\n✅ Sample questions WITH topics:")
            for q in sample_questions:
                print(f"  - Exam: {q[0]}, Topic: {q[2]}")
                print(f"    Question: {q[1][:60]}...")
        
        # Show sample questions without topics
        if questions_without_topics > 0:
            cursor.execute("SELECT exam_id, text FROM questions WHERE topic IS NULL OR topic = '' LIMIT 5")
            sample_questions = cursor.fetchall()
            print("\n❌ Sample questions WITHOUT topics:")
            for q in sample_questions:
                print(f"  - Exam: {q[0]}")
                print(f"    Question: {q[1][:60]}...")
        
        # Check nurse discipline specifically
        print(f"\n👩‍⚕️ NURSE DISCIPLINE CHECK:")
        cursor.execute("""
            SELECT e.id, e.title, e.source, COUNT(q.id) as question_count,
                   COUNT(CASE WHEN q.topic IS NOT NULL AND q.topic != '' THEN 1 END) as questions_with_topics
            FROM exams e
            LEFT JOIN questions q ON e.id = q.exam_id
            WHERE e.discipline_id = 'nurse'
            GROUP BY e.id
        """)
        nurse_exams = cursor.fetchall()
        print(f"Found {len(nurse_exams)} nurse exams:")
        for exam in nurse_exams:
            print(f"  - {exam[0]}: {exam[1]} (Source: {exam[2]})")
            print(f"    Total questions: {exam[3]}, With topics: {exam[4]}")
        
        conn.close()
        
    except Error as e:
        print(f"❌ Database error: {e}")

def test_backend_expectations():
    """Test what fields the backend actually wants"""
    print("\n🧪 TESTING BACKEND API:")
    print("=" * 40)
    
    # Test minimal payload
    test_payload = {
        "title": "Test Quiz - Patient Care",
        "discipline": "nurse",
        "questions": [
            {
                "text": "What is the first step in patient assessment?",
                "options": ["Vital signs", "Health history", "Physical exam", "Lab tests"],
                "correct_idx": 0,
                "topic": "patient_care",  # REQUIRED for Smart Quiz
                "rationale": "Vital signs provide immediate critical information",
                "difficulty": "basic"
            },
            {
                "text": "Which medication requires careful monitoring of blood levels?",
                "options": ["Aspirin", "Warfarin", "Ibuprofen", "Acetaminophen"],
                "correct_idx": 1,
                "topic": "pharmacology",  # REQUIRED for Smart Quiz
                "rationale": "Warfarin has a narrow therapeutic window",
                "difficulty": "intermediate"
            }
        ]
    }
    
    try:
        print("Sending test payload to backend...")
        response = requests.post('https://1006ed2f4c29.ngrok-free.app/quiz/create', json=test_payload)
        print(f"✅ Response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS!")
            print(f"   Quiz ID: {result.get('quiz_id', result.get('exam_id', 'N/A'))}")
            print(f"   Title: {result.get('title', 'N/A')}")
            print(f"   Questions created: {result.get('questions_created', len(test_payload['questions']))}")
            print(f"   Message: {result.get('message', 'N/A')}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    check_database()
    test_backend_expectations()