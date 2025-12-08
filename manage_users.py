# test_connection.py
import sqlite3
import os

print(f"Current directory: {os.getcwd()}")
print(f"Database exists: {os.path.exists('theclamed.db')}")

if os.path.exists('theclamed.db'):
    conn = sqlite3.connect('theclamed.db')
    cursor = conn.cursor()
    
    # Test the exact query from the script
    cursor.execute("""
        SELECT DISTINCT profession, COUNT(*) as user_count
        FROM users 
        WHERE status = 'approved'
        GROUP BY profession
        ORDER BY profession
    """)
    
    professions = cursor.fetchall()
    print(f"\nFound {len(professions)} professions:")
    for prof, count in professions:
        print(f"  {prof}: {count} users")
    
    conn.close()
else:
    print("❌ Database file not found!")