import sqlite3
import os

def delete_all_ai_quizzes():
    """Delete ALL AI-Enhanced and Smart Quizzes from database"""
    
    # Database path - adjust if needed
    db_path = "theclamed.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        
        # Try common locations
        possible_paths = [
            r"d:\Thecla\theclamed.db",
            r"d:\TheclaMed\backend\theclamed.db",
            r"theclamed.db",
            os.path.join(os.getcwd(), "theclamed.db")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                db_path = path
                print(f"✅ Found database at: {db_path}")
                break
        
        if not os.path.exists(db_path):
            print("❌ Could not find database. Please specify path manually.")
            return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n" + "="*60)
        print("🗑️  DELETING ALL AI/SMART QUIZZES")
        print("="*60)
        
        # 1. FIRST, COUNT WHAT WE HAVE
        print("\n📊 CHECKING DATABASE...")
        
        # Count AI/Smart quizzes
        cursor.execute("""
            SELECT COUNT(*) FROM exams 
            WHERE source = 'intelligent' 
            OR title LIKE '%Smart Quiz%'
            OR title LIKE '%AI-Enhanced%'
            OR title LIKE '%AI Enhanced%'
        """)
        ai_quiz_count = cursor.fetchone()[0]
        
        # Count AI/Smart questions
        cursor.execute("""
            SELECT COUNT(*) FROM questions 
            WHERE exam_id IN (
                SELECT id FROM exams 
                WHERE source = 'intelligent' 
                OR title LIKE '%Smart Quiz%'
                OR title LIKE '%AI-Enhanced%'
                OR title LIKE '%AI Enhanced%'
            )
        """)
        ai_question_count = cursor.fetchone()[0]
        
        # Count total quizzes by source
        cursor.execute("SELECT source, COUNT(*) FROM exams GROUP BY source")
        source_counts = cursor.fetchall()
        
        print(f"   AI/Smart Quizzes found: {ai_quiz_count}")
        print(f"   AI/Smart Questions found: {ai_question_count}")
        print(f"   Total quizzes by source:")
        for source, count in source_counts:
            print(f"     • {source}: {count}")
        
        if ai_quiz_count == 0:
            print("\n✅ No AI/Smart quizzes to delete!")
            return
        
        # 2. ASK FOR CONFIRMATION
        print("\n⚠️  WARNING: This will PERMANENTLY delete:")
        print(f"   • {ai_quiz_count} AI/Smart Quizzes")
        print(f"   • {ai_question_count} AI/Smart Questions")
        
        confirm = input("\nType 'DELETE' to confirm: ").strip()
        if confirm != "DELETE":
            print("❌ Deletion cancelled.")
            return
        
        # 3. DISABLE FOREIGN KEYS
        cursor.execute("PRAGMA foreign_keys = OFF")
        print("\n🔓 Foreign keys disabled")
        
        # 4. DELETE QUESTIONS FIRST
        print("\n🗑️  Deleting AI/Smart questions...")
        cursor.execute("""
            DELETE FROM questions 
            WHERE exam_id IN (
                SELECT id FROM exams 
                WHERE source = 'intelligent' 
                OR title LIKE '%Smart Quiz%'
                OR title LIKE '%AI-Enhanced%'
                OR title LIKE '%AI Enhanced%'
            )
        """)
        deleted_questions = cursor.rowcount
        print(f"   ✅ Deleted {deleted_questions} questions")
        
        # 5. DELETE THE QUIZZES
        print("\n🗑️  Deleting AI/Smart quizzes...")
        cursor.execute("""
            DELETE FROM exams 
            WHERE source = 'intelligent' 
            OR title LIKE '%Smart Quiz%'
            OR title LIKE '%AI-Enhanced%'
            OR title LIKE '%AI Enhanced%'
        """)
        deleted_quizzes = cursor.rowcount
        print(f"   ✅ Deleted {deleted_quizzes} quizzes")
        
        # 6. ENABLE FOREIGN KEYS
        cursor.execute("PRAGMA foreign_keys = ON")
        print("\n🔒 Foreign keys re-enabled")
        
        # 7. COMMIT CHANGES
        conn.commit()
        
        # 8. VERIFY DELETION
        print("\n📋 VERIFYING DELETION...")
        
        cursor.execute("""
            SELECT COUNT(*) FROM exams 
            WHERE source = 'intelligent' 
            OR title LIKE '%Smart Quiz%'
            OR title LIKE '%AI-Enhanced%'
        """)
        remaining_ai_quizzes = cursor.fetchone()[0]
        
        cursor.execute("SELECT source, COUNT(*) FROM exams GROUP BY source")
        new_source_counts = cursor.fetchall()
        
        print(f"   Remaining AI/Smart quizzes: {remaining_ai_quizzes}")
        print(f"   New distribution:")
        for source, count in new_source_counts:
            print(f"     • {source}: {count}")
        
        # 9. SHOW WHAT REMAINS
        print("\n📊 REMAINING QUIZZES:")
        cursor.execute("""
            SELECT source, title, COUNT(*) as count 
            FROM exams 
            GROUP BY source, title
            ORDER BY source, title
        """)
        remaining_quizzes = cursor.fetchall()
        
        for source, title, count in remaining_quizzes:
            print(f"   • {source}: {title} ({count} quiz/es)")
        
        conn.close()
        
        print("\n" + "="*60)
        print("✅ DELETION COMPLETE!")
        print("="*60)
        print(f"   Removed: {deleted_quizzes} AI/Smart Quizzes")
        print(f"   Removed: {deleted_questions} AI/Smart Questions")
        print(f"   Remaining AI/Smart Quizzes: {remaining_ai_quizzes}")
        print("\n🎯 Database is now clean! Ready for fresh uploads.")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def check_database_status():
    """Quick check of database status"""
    db_path = "theclamed.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\n📊 DATABASE STATUS CHECK")
        print("="*40)
        
        # Total counts
        cursor.execute("SELECT COUNT(*) FROM exams")
        total_exams = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM questions")
        total_questions = cursor.fetchone()[0]
        
        print(f"Total Exams: {total_exams}")
        print(f"Total Questions: {total_questions}")
        
        # Breakdown by source
        cursor.execute("""
            SELECT 
                source,
                COUNT(*) as exam_count,
                SUM((SELECT COUNT(*) FROM questions q WHERE q.exam_id = e.id)) as question_count
            FROM exams e
            GROUP BY source
            ORDER BY exam_count DESC
        """)
        
        print("\nBreakdown by source:")
        for source, exam_count, question_count in cursor.fetchall():
            print(f"  {source}: {exam_count} exams, {question_count} questions")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("🎯 AI/SMART QUIZ CLEANUP TOOL")
    print("="*60)
    
    # First show current status
    check_database_status()
    
    # Ask user what to do
    print("\n" + "="*60)
    print("OPTIONS:")
    print("1. Delete ALL AI/Smart Quizzes")
    print("2. Just check database status")
    print("3. Exit")
    print("="*60)
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == '1':
        delete_all_ai_quizzes()
    elif choice == '2':
        check_database_status()
    elif choice == '3':
        print("👋 Exiting...")
    else:
        print("❌ Invalid choice")