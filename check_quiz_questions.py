import sqlite3
import os
from datetime import datetime

def check_quiz_questions():
    """Check what quiz questions exist and their labels"""
    
    db_file = "theclamed.db"
    
    if not os.path.exists(db_file):
        print(f"❌ Database file not found: {db_file}")
        print("💡 Make sure you're running this from your backend folder")
        return
    
    print("🔍 Checking quiz questions in database...")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # 1. Check exam types and counts
        print("\n📊 EXAM TYPES BREAKDOWN:")
        print("-" * 30)
        cursor.execute("""
            SELECT source, COUNT(*) as count 
            FROM exams 
            GROUP BY source
        """)
        exam_types = cursor.fetchall()
        for source, count in exam_types:
            print(f"   {source}: {count} exams")
        
        # 2. Check total questions by exam type
        print("\n❓ QUESTIONS BY EXAM TYPE:")
        print("-" * 30)
        cursor.execute("""
            SELECT e.source, COUNT(q.id) as question_count
            FROM exams e
            LEFT JOIN questions q ON e.id = q.exam_id
            GROUP BY e.source
        """)
        questions_by_source = cursor.fetchall()
        for source, count in questions_by_source:
            print(f"   {source}: {count} questions")
        
        # 3. Check labeled questions for QUIZ exams (plural source)
        print("\n🏷️  LABELED QUIZ QUESTIONS (for Smart Quiz):")
        print("-" * 40)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_quiz_questions,
                SUM(CASE WHEN q.topic IS NOT NULL THEN 1 ELSE 0 END) as labeled_questions,
                SUM(CASE WHEN q.topic IS NULL THEN 1 ELSE 0 END) as unlabeled_questions
            FROM questions q
            JOIN exams e ON q.exam_id = e.id
            WHERE e.source = 'plural'
        """)
        quiz_stats = cursor.fetchone()
        total, labeled, unlabeled = quiz_stats
        print(f"   Total quiz questions: {total}")
        print(f"   Labeled with topics: {labeled}")
        print(f"   Unlabeled: {unlabeled}")
        
        if total > 0:
            labeling_percentage = (labeled / total) * 100
            print(f"   Labeling progress: {labeling_percentage:.1f}%")
        
        # 4. Show available topics
        print("\n📚 AVAILABLE TOPICS:")
        print("-" * 20)
        cursor.execute("""
            SELECT topic, COUNT(*) as count
            FROM questions 
            WHERE topic IS NOT NULL
            GROUP BY topic
            ORDER BY count DESC
        """)
        topics = cursor.fetchall()
        
        if topics:
            for topic, count in topics:
                print(f"   {topic}: {count} questions")
        else:
            print("   ❌ No topics found - questions need labeling!")
        
        # 5. Show sample of unlabeled quiz questions
        print("\n🔍 SAMPLE UNLABELED QUIZ QUESTIONS:")
        print("-" * 35)
        cursor.execute("""
            SELECT q.text, e.title as exam_title
            FROM questions q
            JOIN exams e ON q.exam_id = e.id
            WHERE e.source = 'plural' AND q.topic IS NULL
            LIMIT 5
        """)
        unlabeled_samples = cursor.fetchall()
        
        if unlabeled_samples:
            for i, (text, exam_title) in enumerate(unlabeled_samples, 1):
                preview = text[:80] + "..." if len(text) > 80 else text
                print(f"   {i}. [{exam_title}] {preview}")
        else:
            print("   ✅ All quiz questions are labeled!")
        
        # 6. Smart Quiz readiness check
        print("\n🎯 SMART QUIZ READINESS:")
        print("-" * 25)
        if labeled >= 10:
            print("   ✅ READY! You have enough labeled questions for Smart Quiz")
            print(f"   📈 Status: {labeled} labeled questions available")
        else:
            print("   ❌ NOT READY: Need at least 10 labeled quiz questions")
            print(f"   📉 Status: Only {labeled} labeled questions available")
            if unlabeled > 0:
                print(f"   💡 Tip: Run auto-labeling on {unlabeled} unlabeled questions")
        
        print("\n" + "=" * 60)
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        if conn:
            conn.close()

def auto_label_questions():
    """Auto-label unlabeled questions (if needed)"""
    print("\n🔄 Would you like to auto-label unlabeled questions?")
    choice = input("   Enter 'y' to auto-label or any other key to skip: ").strip().lower()
    
    if choice == 'y':
        print("   Running auto-labeling...")
        # You would call your auto-labeling function here
        # For now, just show message
        print("   💡 Auto-labeling would run here")
        print("   🔗 Visit: https://1006ed2f4c29.ngrok-free.app/admin/auto-label-questions")
    else:
        print("   Skipping auto-labeling")

if __name__ == "__main__":
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    check_quiz_questions()
    auto_label_questions()