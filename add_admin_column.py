import sqlite3

# Connect to your database
conn = sqlite3.connect('theclamed.db')
cursor = conn.cursor()

print("🔍 Fixing database: adding admin columns...")

# Add is_admin column if not exists
try:
    cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
    print("✅ Added is_admin column")
except sqlite3.OperationalError:
    print("✅ is_admin column already exists")

# Add role column if not exists  
try:
    cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    print("✅ Added role column")
except sqlite3.OperationalError:
    print("✅ role column already exists")

# Save changes
conn.commit()

# Show what we have
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()

print("\n📋 Current users table structure:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

conn.close()
print("\n✅ Database fixed! Now run /create-admin endpoint")