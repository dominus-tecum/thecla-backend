import sqlite3

conn = sqlite3.connect('theclamed.db')
cursor = conn.cursor()

print('🔍 Checking DailyUsageTracking columns...')
cursor.execute('PRAGMA table_info(daily_usage_tracking)')
columns = [col[1] for col in cursor.fetchall()]
print('Current columns:', columns)

# Add missing columns
if 'simulation_count' not in columns:
    cursor.execute('ALTER TABLE daily_usage_tracking ADD COLUMN simulation_count INTEGER DEFAULT 0')
    print('✅ Added simulation_count column')

if 'procedure_count' not in columns:
    cursor.execute('ALTER TABLE daily_usage_tracking ADD COLUMN procedure_count INTEGER DEFAULT 0')
    print('✅ Added procedure_count column')

if 'ai_quiz_questions_count' not in columns:
    cursor.execute('ALTER TABLE daily_usage_tracking ADD COLUMN ai_quiz_questions_count INTEGER DEFAULT 0')
    print('✅ Added ai_quiz_questions_count column')

conn.commit()
conn.close()
print('\n✅ Database columns fixed!')