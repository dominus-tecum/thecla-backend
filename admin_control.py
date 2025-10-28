import requests
import json
from datetime import datetime
import sqlite3
import os

# ===== DEBUG: CHECK DATABASE CONNECTION =====
def check_database_connection():
    print("🔍 DEBUG: Checking database connection...")
    print("=" * 50)
    
    # ✅ CORRECTED DATABASE PATH
    db_path = r"D:\TheclaMed\backend\theclamed.db"
    db_full_path = os.path.abspath(db_path)
    
    print(f"📁 Looking for database at: {db_full_path}")
    
    if os.path.exists(db_path):
        print("✅ Database file EXISTS")
        print(f"📏 File size: {os.path.getsize(db_path)} bytes")
        
        # Check what's inside the database
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # List all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print("📋 Tables in database:")
            for table in tables:
                print(f"   - {table[0]}")
            
            # Check exams table structure
            print("\n🔍 Exams table structure:")
            cursor.execute("PRAGMA table_info(exams)")
            columns = cursor.fetchall()
            for col in columns:
                print(f"   - {col[1]} ({col[2]})")
            
            # Check if there's any data
            cursor.execute("SELECT COUNT(*) FROM exams")
            exam_count = cursor.fetchone()[0]
            print(f"\n📊 Number of exams in database: {exam_count}")
            
            if exam_count > 0:
                cursor.execute("SELECT id, title, is_released FROM exams LIMIT 5")
                exams = cursor.fetchall()
                print("📝 Sample exams:")
                for exam in exams:
                    print(f"   - {exam[0]}: {exam[1]} (released: {exam[2]})")
            
            conn.close()
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            print("=" * 50)
    else:
        print("❌ Database file NOT FOUND")
        print("=" * 50)

# ===== RUN THE DEBUG CHECK =====
check_database_connection()

API_URL = 'https://thecla-backend.onrender.com'

# ===== NEW: COMPARE DATABASES FUNCTION =====
def compare_databases():
    """Compare what's in local DB vs what API returns"""
    print("\n🔍 COMPARING DATABASES")
    print("=" * 50)
    
    # Check local database (D:\TheclaMed\backend\theclamed.db)
    db_path = r"D:\TheclaMed\backend\theclamed.db"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, title FROM exams")
        local_exams = cursor.fetchall()
        conn.close()
        print(f"📁 LOCAL DB ({db_path}): {len(local_exams)} exams")
        for exam in local_exams:
            print(f"   - {exam[0]}: {exam[1]}")
    else:
        print(f"❌ Local database not found: {db_path}")
    
    print("\n" + "=" * 50)
    
    # Check what backend API returns
    try:
        response = requests.get(f"{API_URL}/admin/exams")
        if response.status_code == 200:
            api_exams = response.json()
            print(f"🌐 API/NGROK DB: {len(api_exams)} exams")
            for exam in api_exams:
                print(f"   - {exam['id']}: {exam['title']}")
            
            # Check for mismatches
            local_ids = {exam[0] for exam in local_exams}
            api_ids = {exam['id'] for exam in api_exams}
            
            print(f"\n🔍 COMPARISON RESULTS:")
            print(f"   Local-only exams: {len(local_ids - api_ids)}")
            print(f"   API-only exams: {len(api_ids - local_ids)}")
            print(f"   Common exams: {len(local_ids & api_ids)}")
            
        else:
            print(f"❌ API failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"💥 API error: {e}")

# ===== USER MANAGEMENT FUNCTIONS =====

def list_all_users():
    """Get list of all users in the system"""
    print("\n👥 LISTING ALL USERS")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_URL}/admin/users")
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            users = response.json()
            print(f"📊 Found {len(users)} users in system:")
            print("\n" + "-" * 50)
            
            for i, user in enumerate(users, 1):
                print(f"{i}. ID: {user['user_id']}")
                print(f"   Name: {user['name']}")
                print(f"   Email: {user['email']}")
                print(f"   Profession: {user['profession']}")
                print(f"   Created: {user['created_at']}")
                print("-" * 30)
            
            return users
        else:
            print(f"❌ Failed to fetch users: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return []

def get_user_exam_access(user_id):
    """Get exams that a specific user has access to"""
    print(f"\n🔍 GETTING EXAM ACCESS FOR USER {user_id}")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_URL}/admin/users/{user_id}/exams")
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            user_exams = response.json()
            print(f"📊 User has access to {len(user_exams)} exams:")
            print("\n" + "-" * 50)
            
            for i, exam in enumerate(user_exams, 1):
                status = "🟢 ACCESS" if exam['has_access'] else "🔴 NO ACCESS"
                print(f"{i}. {exam['exam_title']}")
                print(f"   Exam ID: {exam['exam_id']}")
                print(f"   Status: {status}")
                if exam['assigned_at']:
                    print(f"   Assigned: {exam['assigned_at']}")
                print("-" * 30)
            
            return user_exams
        else:
            print(f"❌ Failed to fetch user exams: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return []

def grant_exam_access_to_user(user_id, exam_id):
    """Grant a specific exam access to a specific user"""
    print(f"\n🎯 GRANTING EXAM ACCESS")
    print("=" * 50)
    print(f"👤 User ID: {user_id}")
    print(f"📝 Exam ID: {exam_id}")
    
    try:
        response = requests.post(
            f"{API_URL}/admin/users/{user_id}/exams/{exam_id}/grant-access"
        )
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS: {result['msg']}")
            return True
        else:
            print(f"❌ FAILED: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return False

def revoke_exam_access_from_user(user_id, exam_id):
    """Revoke exam access from a specific user"""
    print(f"\n⛔ REVOKING EXAM ACCESS")
    print("=" * 50)
    print(f"👤 User ID: {user_id}")
    print(f"📝 Exam ID: {exam_id}")
    
    try:
        response = requests.post(
            f"{API_URL}/admin/users/{user_id}/exams/{exam_id}/revoke-access"
        )
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS: {result['msg']}")
            return True
        else:
            print(f"❌ FAILED: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return False

def grant_exam_to_multiple_users():
    """Grant exam access to multiple users at once"""
    print("\n👥 GRANT EXAM TO MULTIPLE USERS")
    print("=" * 50)
    
    # List all exams
    exams = debug_list_all_exams_with_ids()
    if not exams:
        return
    
    # Get exam ID
    exam_id = input("Enter exam ID to grant: ").strip()
    if not exam_id:
        print("❌ Please enter a valid exam ID")
        return
    
    # Verify exam exists
    exam = next((e for e in exams if e['id'] == exam_id), None)
    if not exam:
        print("❌ Exam ID not found")
        return
    
    print(f"📝 Selected exam: {exam['title']}")
    
    # List all users
    users = list_all_users()
    if not users:
        return
    
    # Get user IDs
    user_ids_input = input("Enter user IDs (comma-separated): ").strip()
    if not user_ids_input:
        print("❌ Please enter at least one user ID")
        return
    
    user_ids = [uid.strip() for uid in user_ids_input.split(',')]
    
    print(f"\n🎯 Granting '{exam['title']}' to {len(user_ids)} users...")
    print("=" * 50)
    
    success_count = 0
    for user_id in user_ids:
        # Verify user exists
        user = next((u for u in users if str(u['user_id']) == user_id), None)
        if not user:
            print(f"❌ User ID {user_id} not found - skipping")
            continue
        
        if grant_exam_access_to_user(user_id, exam_id):
            success_count += 1
            print(f"✅ Granted to user {user_id} ({user['name']})")
        else:
            print(f"❌ Failed to grant to user {user_id}")
    
    print(f"\n🎉 Successfully granted access to {success_count}/{len(user_ids)} users")

def manage_user_specific_exams():
    """Manage exam access for a specific user"""
    print("\n👤 MANAGE USER-SPECIFIC EXAMS")
    print("=" * 50)
    
    # List all users
    users = list_all_users()
    if not users:
        return
    
    # Get user ID
    user_id = input("Enter user ID to manage: ").strip()
    if not user_id:
        print("❌ Please enter a valid user ID")
        return
    
    # Verify user exists
    user = next((u for u in users if str(u['user_id']) == user_id), None)
    if not user:
        print("❌ User ID not found")
        return
    
    print(f"👤 Managing exams for: {user['name']} ({user['email']})")
    
    while True:
        print("\n" + "=" * 40)
        print(f"USER: {user['name']} (ID: {user_id})")
        print("=" * 40)
        print("1. 📋 View current exam access")
        print("2. ➕ Grant new exam access")
        print("3. ❌ Revoke exam access")
        print("4. ↩️ Back to main menu")
        print("=" * 40)
        
        choice = input("Enter choice (1-4): ").strip()
        
        if choice == '1':
            get_user_exam_access(user_id)
        
        elif choice == '2':
            exams = debug_list_all_exams_with_ids()
            if exams:
                exam_id = input("Enter exam ID to grant: ").strip()
                if exam_id:
                    grant_exam_access_to_user(user_id, exam_id)
                else:
                    print("❌ Please enter a valid exam ID")
        
        elif choice == '3':
            user_exams = get_user_exam_access(user_id)
            accessible_exams = [e for e in user_exams if e['has_access']]
            
            if accessible_exams:
                exam_id = input("Enter exam ID to revoke: ").strip()
                if exam_id:
                    revoke_exam_access_from_user(user_id, exam_id)
                else:
                    print("❌ Please enter a valid exam ID")
            else:
                print("ℹ️ User has no exam access to revoke")
        
        elif choice == '4':
            break
        
        else:
            print("❌ Invalid choice")
        
        input("\nPress Enter to continue...")

# ===== EXISTING FUNCTIONS (UPDATED PATHS) =====

def debug_list_all_exams_with_ids():
    """Debug function to see all exams with their exact IDs"""
    print("\n🔍 DEBUG: LISTING ALL EXAMS WITH IDs")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_URL}/admin/exams")
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            exams = response.json()
            print(f"📊 Found {len(exams)} exams in system:")
            print("\n" + "-" * 50)
            
            for i, exam in enumerate(exams, 1):
                status = "🟢 RELEASED" if exam['is_released'] else "🔴 UNRELEASED"
                print(f"{i}. ID: '{exam['id']}'")
                print(f"   Title: {exam['title']}")
                print(f"   Discipline: {exam['discipline_id']}")
                print(f"   Source: {exam['source']}")
                print(f"   Status: {status}")
                print(f"   Questions: {exam['question_count']}")
                print("-" * 30)
            
            if not exams:
                print("❌ No exams found in the system!")
                print("💡 You need to create some exams first.")
            
            return exams
        else:
            print(f"❌ Failed to fetch exams: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return []

def list_all_exams():
    """List all exams (including unreleased)"""
    print("\n📋 LISTING ALL EXAMS")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_URL}/admin/exams")
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            exams = response.json()
            print(f"🔍 Got {len(exams)} exams from API")
            
            if not exams:
                print("❌ No exams found in the system")
                return []
            
            print(f"📊 Total exams: {len(exams)}")
            print("\n" + "-" * 50)
            
            for i, exam in enumerate(exams, 1):
                status = "🟢 RELEASED" if exam['is_released'] else "🔴 UNRELEASED"
                release_info = f"Released: {exam['release_date']}" if exam['release_date'] else "Not released"
                
                print(f"{i}. {exam['title']}")
                print(f"   ID: {exam['id']}")
                print(f"   Discipline: {exam['discipline_id']}")
                print(f"   Source: {exam['source']}")
                print(f"   Status: {status}")
                print(f"   {release_info}")
                print(f"   Questions: {exam['question_count']}")
                print("-" * 30)
            
            return exams
        else:
            print(f"❌ Failed to fetch exams: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return []

def list_exams_by_discipline(discipline):
    """List exams for a specific discipline"""
    print(f"\n🎯 EXAMS FOR {discipline.upper()}")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_URL}/admin/exams?discipline_id={discipline}")
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            exams = response.json()
            print(f"🔍 Got {len(exams)} exams from API for {discipline}")
            
            if not exams:
                print(f"❌ No exams found for {discipline}")
                return []
            
            released = [e for e in exams if e['is_released']]
            unreleased = [e for e in exams if not e['is_released']]
            
            print(f"📊 Total: {len(exams)} | 🟢 Released: {len(released)} | 🔴 Unreleased: {len(unreleased)}")
            print("\n" + "-" * 50)
            
            for i, exam in enumerate(exams, 1):
                status = "🟢 RELEASED" if exam['is_released'] else "🔴 UNRELEASED"
                print(f"{i}. {exam['title']} | {status}")
            
            return exams
        else:
            print(f"❌ Failed to fetch {discipline} exams: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return []

def release_exam(exam_id):
    """Release a specific exam"""
    print(f"\n🚀 RELEASING EXAM: {exam_id}")
    print("=" * 50)
    
    try:
        response = requests.post(f"{API_URL}/admin/exams/{exam_id}/release")
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS: {result['msg']}")
            print(f"📅 Release date: {result['release_date']}")
            return True
        else:
            print(f"❌ FAILED: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return False

def unrelease_exam(exam_id):
    """Unrelease/recall a specific exam"""
    print(f"\n⏸️ UNRELEASING EXAM: {exam_id}")
    print("=" * 50)
    
    try:
        response = requests.post(f"{API_URL}/admin/exams/{exam_id}/unrelease")
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS: {result['msg']}")
            return True
        else:
            print(f"❌ FAILED: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return False

def release_all_unreleased(discipline=None):
    """Release all unreleased exams (optionally filtered by discipline)"""
    print(f"\n🎯 RELEASING ALL UNRELEASED EXAMS" + (f" FOR {discipline.upper()}" if discipline else ""))
    print("=" * 50)
    
    try:
        if discipline:
            exams = list_exams_by_discipline(discipline)
        else:
            exams = list_all_exams()
        
        unreleased_exams = [e for e in exams if not e['is_released']]
        
        if not unreleased_exams:
            print("✅ All exams are already released!")
            return
        
        print(f"\n📦 Found {len(unreleased_exams)} unreleased exams")
        
        success_count = 0
        for exam in unreleased_exams:
            if release_exam(exam['id']):
                success_count += 1
        
        print(f"\n🎉 Released {success_count}/{len(unreleased_exams)} exams successfully!")
        
    except Exception as e:
        print(f"💥 Error: {e}")

def get_system_stats():
    """Get system statistics"""
    print("\n📊 SYSTEM STATISTICS")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_URL}/admin/exams")
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            exams = response.json()
            print(f"🔍 Got {len(exams)} exams for statistics")
            
            # Count by discipline
            disciplines = {}
            for exam in exams:
                disc = exam['discipline_id']
                if disc not in disciplines:
                    disciplines[disc] = {'total': 0, 'released': 0, 'unreleased': 0}
                
                disciplines[disc]['total'] += 1
                if exam['is_released']:
                    disciplines[disc]['released'] += 1
                else:
                    disciplines[disc]['unreleased'] += 1
            
            # Count by source
            sources = {'singular': 0, 'plural': 0}
            for exam in exams:
                sources[exam['source']] += 1
            
            print(f"📈 Total Exams: {len(exams)}")
            print(f"📚 Singular (Reading): {sources['singular']}")
            print(f"📝 Plural (Interactive): {sources['plural']}")
            
            print("\n🏥 BY DISCIPLINE:")
            for disc, stats in disciplines.items():
                released_pct = (stats['released'] / stats['total']) * 100 if stats['total'] > 0 else 0
                print(f"   {disc.upper():<15} | Total: {stats['total']:>2} | 🟢 Released: {stats['released']:>2} | 🔴 Unreleased: {stats['unreleased']:>2} | {released_pct:>5.1f}%")
            
        else:
            print(f"❌ Failed to get stats: {response.status_code}")
            
    except Exception as e:
        print(f"💥 Error: {e}")

def show_menu():
    """Display admin menu"""
    print("\n" + "=" * 60)
    print("🎛️  EXAM ADMIN CONTROL PANEL")
    print("=" * 60)
    print("1. 📋 List all exams")
    print("2. 👩‍⚕️ List Nurse exams")
    print("3. 👨‍⚕️ List GP exams")
    print("4. 🚀 Release specific exam")
    print("5. ⏸️  Unrelease specific exam")
    print("6. 🎯 Release all unreleased Nurse exams")
    print("7. 🎯 Release all unreleased GP exams")
    print("8. 📊 System statistics")
    print("9. 🔍 DEBUG: List all exams with IDs")
    print("10. 🔄 COMPARE DATABASES (NEW)")
    print("=" * 60)
    print("👥 USER-SPECIFIC EXAM MANAGEMENT")
    print("=" * 60)
    print("11. 👥 List all users")
    print("12. 👤 Manage exams for specific user")
    print("13. ➕ Grant exam to multiple users")
    print("14. 🔍 Check user's exam access")
    print("=" * 60)
    print("15. 🚪 Exit")
    print("=" * 60)

def main():
    """Main admin control loop"""
    print("🔐 Welcome to Exam Admin Control Panel")
    
    while True:
        show_menu()
        choice = input("\nEnter your choice (1-15): ").strip()
        
        if choice == '1':
            list_all_exams()
        
        elif choice == '2':
            list_exams_by_discipline('nurse')
        
        elif choice == '3':
            list_exams_by_discipline('gp')
        
        elif choice == '4':
            exam_id = input("Enter exam ID to release: ").strip()
            if exam_id:
                release_exam(exam_id)
            else:
                print("❌ Please enter a valid exam ID")
        
        elif choice == '5':
            exam_id = input("Enter exam ID to unrelease: ").strip()
            if exam_id:
                unrelease_exam(exam_id)
            else:
                print("❌ Please enter a valid exam ID")
        
        elif choice == '6':
            release_all_unreleased('nurse')
        
        elif choice == '7':
            release_all_unreleased('gp')
        
        elif choice == '8':
            get_system_stats()
        
        elif choice == '9':
            debug_list_all_exams_with_ids()
        
        elif choice == '10':
            compare_databases()
        
        # USER-SPECIFIC FUNCTIONS
        elif choice == '11':
            list_all_users()
        
        elif choice == '12':
            manage_user_specific_exams()
        
        elif choice == '13':
            grant_exam_to_multiple_users()
        
        elif choice == '14':
            user_id = input("Enter user ID to check access: ").strip()
            if user_id:
                get_user_exam_access(user_id)
            else:
                print("❌ Please enter a valid user ID")
        
        elif choice == '15':
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    main()