import sqlite3
import os
import shutil
from datetime import datetime

def migrate_database():
    """Migrate the database to add missing columns without losing data"""
    
    db_file = "theclamed.db"
    backup_file = f"theclamed_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    print("🔧 Starting database migration...")
    
    # Create backup
    if os.path.exists(db_file):
        shutil.copy2(db_file, backup_file)
        print(f"✅ Backup created: {backup_file}")
    else:
        print("❌ Database file not found!")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Check current schema
        cursor.execute("PRAGMA table_info(questions)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Current question columns: {columns}")
        
        # Add missing columns if they don't exist
        if 'topic' not in columns:
            cursor.execute("ALTER TABLE questions ADD COLUMN topic TEXT")
            print("✅ Added 'topic' column")
        
        if 'subtopic' not in columns:
            cursor.execute("ALTER TABLE questions ADD COLUMN subtopic TEXT")
            print("✅ Added 'subtopic' column")
        
        if 'difficulty' not in columns:
            cursor.execute("ALTER TABLE questions ADD COLUMN difficulty TEXT")
            print("✅ Added 'difficulty' column")
        
        # Check exam table
        cursor.execute("PRAGMA table_info(exams)")
        exam_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Current exam columns: {exam_columns}")
        
        # Add missing columns to exams table if needed
        exam_new_columns = ['topic', 'subtopic', 'difficulty', 'concepts']
        for col in exam_new_columns:
            if col not in exam_columns:
                cursor.execute(f"ALTER TABLE exams ADD COLUMN {col} TEXT")
                print(f"✅ Added '{col}' column to exams")
        
        conn.commit()
        conn.close()
        
        print("🎉 Database migration completed successfully!")
        print("📊 You can now run your FastAPI server")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print(f"🔄 Restoring from backup...")
        
        # Restore backup if migration failed
        if os.path.exists(backup_file):
            shutil.copy2(backup_file, db_file)
            print("✅ Database restored from backup")
        
        return False

if __name__ == "__main__":
    migrate_database()