import sqlite3

conn = sqlite3.connect('theclamed.db')
cursor = conn.cursor()

print('🔍 ALL USERS IN DATABASE:')
cursor.execute('SELECT id, email, status, is_admin, role FROM users')
users = cursor.fetchall()

for user in users:
    print(f'ID {user[0]}: {user[1]}')
    print(f'  Status: {user[2]}')
    print(f'  Is Admin: {user[3]}')
    print(f'  Role: {user[4]}')
    print()

print('🔍 Checking login for admin@thecla.com:')
cursor.execute('SELECT hashed_password FROM users WHERE email="admin@thecla.com"')
result = cursor.fetchone()
if result:
    print('✅ User exists')
    print(f'✅ Password hash: {result[0][:50]}...')
else:
    print('❌ User not found')

conn.close()