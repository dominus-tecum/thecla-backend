#!/usr/bin/env python3
"""
SELF-SERVICE ADMIN PASSWORD CHANGER
Run this anytime to change your admin password
"""

import bcrypt
import sqlite3
import getpass
import sys
import os

def change_admin_password():
    print("\n" + "="*50)
    print("🔐 ADMIN PASSWORD CHANGE TOOL")
    print("="*50)
    
    # Configuration
    DB_FILE = "theclamed.db"
    ADMIN_EMAIL = "admin@theclamedical.com"
    
    # Check if database exists
    if not os.path.exists(DB_FILE):
        print(f"❌ Database file '{DB_FILE}' not found!")
        print("\nLooking for database...")
        db_files = [f for f in os.listdir('.') if f.endswith(('.db', '.sqlite'))]
        if db_files:
            print(f"Found database files: {db_files}")
            DB_FILE = db_files[0]
            print(f"Using: {DB_FILE}")
        else:
            print("No database files found in current directory.")
            return
    
    try:
        # Connect to database
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Get admin user
        cursor.execute("SELECT id, email, hashed_password FROM users WHERE email = ?", (ADMIN_EMAIL,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ Admin user '{ADMIN_EMAIL}' not found!")
            
            # Show all users
            cursor.execute("SELECT id, email FROM users LIMIT 5")
            all_users = cursor.fetchall()
            print(f"\nAvailable users (first 5):")
            for uid, email in all_users:
                print(f"  ID {uid}: {email}")
            
            conn.close()
            return
        
        user_id, user_email, current_hash = user
        
        print(f"\n👤 Admin User: {user_email} (ID: {user_id})")
        print("-" * 50)
        
        # Step 1: Verify current password
        print("\n1️⃣ VERIFY CURRENT PASSWORD")
        current_password = getpass.getpass("Enter CURRENT password: ")
        
        try:
            if not bcrypt.checkpw(current_password.encode('utf-8'), current_hash.encode('utf-8')):
                print("❌ Current password is INCORRECT!")
                conn.close()
                return
            print("✅ Current password verified")
        except Exception as e:
            print(f"❌ Password verification failed: {e}")
            conn.close()
            return
        
        # Step 2: Get new password
        print("\n2️⃣ SET NEW PASSWORD")
        while True:
            new_password = getpass.getpass("Enter NEW password: ")
            confirm_password = getpass.getpass("Confirm NEW password: ")
            
            if new_password != confirm_password:
                print("❌ Passwords don't match! Try again.")
                continue
            
            if len(new_password) < 6:
                print("⚠️  Password should be at least 6 characters")
                continue
            
            if new_password == current_password:
                print("❌ New password must be different from current password")
                continue
            
            break
        
        # Step 3: Generate new hash
        print("\n3️⃣ UPDATING PASSWORD...")
        new_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Step 4: Update database
        cursor.execute(
            "UPDATE users SET hashed_password = ? WHERE id = ?",
            (new_hash, user_id)
        )
        
        conn.commit()
        conn.close()
        
        # Success message
        print("\n" + "="*50)
        print("✅ PASSWORD CHANGED SUCCESSFULLY!")
        print("="*50)
        print(f"\n📋 Details:")
        print(f"   User: {user_email}")
        print(f"   New Password: {new_password}")
        print(f"\n💡 Next steps:")
        print(f"   1. Use new password to login")
        print(f"   2. Store password securely")
        print(f"   3. Delete any old password notes")
        print("\n🔒 Security tip: Use a password manager!")
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def show_help():
    print("\n📖 HOW TO USE:")
    print("="*50)
    print("1. Save this file as 'change_admin_password.py'")
    print("2. Run: python change_admin_password.py")
    print("3. Follow the prompts")
    print("\n📁 Requirements:")
    print("   - Python 3.x")
    print("   - bcrypt library: pip install bcrypt")
    print("   - Database file in same directory")
    print("\n⚠️  Security:")
    print("   - Run in secure environment")
    print("   - Don't share your password")
    print("   - Use strong passwords")

def check_dependencies():
    try:
        import bcrypt
        return True
    except ImportError:
        print("\n❌ Missing dependency: bcrypt")
        print("\nInstall it with:")
        print("   pip install bcrypt")
        print("\nOr on some systems:")
        print("   python -m pip install bcrypt")
        return False

if __name__ == "__main__":
    print("\n⚡ Admin Password Self-Service Tool")
    print("="*50)
    
    # Check for help flag
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
        sys.exit(0)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Run the password changer
    change_admin_password()