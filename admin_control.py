import requests
import json
from datetime import datetime
import sqlite3
import os

API_URL = 'https://thecla-backend.onrender.com'

#API_URL = 'https://53a15f117877.ngrok-free.app'

def list_exams_menu():
    """Sub-menu for listing exams by profession"""
    while True:
        print("\n" + "=" * 50)
        print("📋 LIST EXAMS BY PROFESSION")
        print("=" * 50)
        print("1. 👨‍⚕️  List ALL Exams")
        print("2. 👩‍⚕️  List Nurse Exams")
        print("3. 👨‍⚕️  List GP Exams")
        print("4. 🤰  List Midwife Exams")
        print("5. 🔬  List Lab Technologist Exams")
        print("6. 💪  List Physiotherapist Exams")
        print("7. 🏥  List ICU Nurse Exams")
        print("8. 🚑  List Emergency Nurse Exams")
        print("9. 👶  List Neonatal Nurse Exams")
        print("0. ↩️  Back to Main Menu")
        print("=" * 50)
        
        choice = input("\nEnter your choice (0-9): ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            list_all_exams()  # ← TO THIS
        elif choice == '2':
            list_exams_by_discipline('nurse')
        elif choice == '3':
            list_exams_by_discipline('gp')
        elif choice == '4':
            list_exams_by_discipline('midwife')
        elif choice == '5':
            list_exams_by_discipline('lab_tech')
        elif choice == '6':
            list_exams_by_discipline('physiotherapist')
        elif choice == '7':
            list_exams_by_discipline('icu_nurse')
        elif choice == '8':
            list_exams_by_discipline('emergency_nurse')
        elif choice == '9':
            list_exams_by_discipline('neonatal_nurse')
        else:
            print("❌ Invalid choice. Please enter 0-9")
        
        input("\nPress Enter to continue...")



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




def debug_list_all_exams_with_ids():
    """List all exams with IDs for selection"""
    try:
        response = requests.get(f"{API_URL}/admin/exams")
        if response.status_code == 200:
            return response.json()
        return []
    except:
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



def list_all_exams():
    """List all exams (including unreleased)"""
    print("\n📋 LISTING ALL EXAMS (ONLY EXAMS, NOT NOTES)")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_URL}/admin/exams")
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            all_exams = response.json()
            # FILTER: Only show exams with source='plural'
            exams = [exam for exam in all_exams if exam.get('source') == 'plural']
            
            print(f"🔍 Got {len(exams)} EXAMS (filtered from {len(all_exams)} total items)")
            
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
    print(f"\n🎯 EXAMS FOR {discipline.upper()} (ONLY EXAMS, NOT NOTES)")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_URL}/admin/exams?discipline_id={discipline}")
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            all_items = response.json()
            # FILTER: Only show exams with source='plural'
            exams = [exam for exam in all_items if exam.get('source') == 'plural']
            
            print(f"🔍 Got {len(exams)} EXAMS from API for {discipline}")
            
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


def list_notes_menu():
    """Sub-menu for listing study notes by profession"""
    while True:
        print("\n" + "=" * 50)
        print("📚 LIST STUDY NOTES BY PROFESSION")
        print("=" * 50)
        print("1. 👨‍⚕️  List ALL Study Notes")
        print("2. 👩‍⚕️  List Nurse Notes")
        print("3. 👨‍⚕️  List GP Notes")
        print("4. 🤰  List Midwife Notes")
        print("5. 🔬  List Lab Technologist Notes")
        print("6. 💪  List Physiotherapist Notes")
        print("7. 🏥  List ICU Nurse Notes")
        print("8. 🚑  List Emergency Nurse Notes")
        print("9. 👶  List Neonatal Nurse Notes")
        print("0. ↩️  Back to Main Menu")
        print("=" * 50)
        
        choice = input("\nEnter your choice (0-9): ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            list_all_notes()
        elif choice == '2':
            list_notes_by_discipline('nurse')
        elif choice == '3':
            list_notes_by_discipline('gp')
        elif choice == '4':
            list_notes_by_discipline('midwife')
        elif choice == '5':
            list_notes_by_discipline('lab_tech')
        elif choice == '6':
            list_notes_by_discipline('physiotherapist')
        elif choice == '7':
            list_notes_by_discipline('icu_nurse')
        elif choice == '8':
            list_notes_by_discipline('emergency_nurse')
        elif choice == '9':
            list_notes_by_discipline('neonatal_nurse')
        else:
            print("❌ Invalid choice. Please enter 0-9")
        
        input("\nPress Enter to continue...")




def list_all_notes():
    """List all study notes (using /exam endpoint)"""
    print("\n📚 LISTING ALL STUDY NOTES")
    print("=" * 50)
    
    try:
        # CHANGE THIS LINE: Use admin endpoint instead of /exam
        response = requests.get(f"{API_URL}/admin/exams")
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            all_exams = response.json()
            # FILTER: Only show study notes with source='singular'
            notes = [exam for exam in all_exams if exam.get('source') == 'singular']
            
            print(f"📚 Found {len(notes)} study notes:")
            
            for i, note in enumerate(notes, 1):
                print(f"{i}. {note['title']} (Discipline: {note.get('discipline_id', 'Unknown')})")
            
            return notes
        else:
            print(f"❌ Failed to fetch notes: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return []





def list_notes_by_discipline(discipline):
    """List study notes for a specific discipline (using /exam endpoint)"""
    print(f"\n📚 STUDY NOTES FOR {discipline.upper()}")
    print("=" * 50)
    
    try:
        # CHANGE THIS LINE: Use admin endpoint instead of /exam
        response = requests.get(f"{API_URL}/admin/exams")
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            all_exams = response.json()
            # FILTER: Only show study notes with source='singular' AND matching discipline
            notes = [exam for exam in all_exams if exam.get('source') == 'singular' and exam.get('discipline_id') == discipline]
            
            print(f"📚 Found {len(notes)} study notes for {discipline}:")
            
            for i, note in enumerate(notes, 1):
                print(f"{i}. {note['title']}")
            
            return notes
        else:
            print(f"❌ Failed to fetch notes: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return []




def release_exam_menu():
    """Sub-menu for releasing exams by profession"""
    while True:
        print("\n" + "=" * 50)
        print("🚀 RELEASE EXAM BY PROFESSION")
        print("=" * 50)
        print("1. 👨‍⚕️  Release GP Exam")
        print("2. 👩‍⚕️  Release Nurse Exam") 
        print("3. 🤰  Release Midwife Exam")
        print("4. 🔬  Release Lab Technologist Exam")
        print("5. 💪  Release Physiotherapist Exam")
        print("6. 🏥  Release ICU Nurse Exam")
        print("7. 🚑  Release Emergency Nurse Exam")
        print("8. 👶  Release Neonatal Nurse Exam")
        print("9. 📋  List all exams with IDs")
        print("0. ↩️  Back to Main Menu")
        print("=" * 50)
        
        choice = input("\nEnter your choice (0-9): ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            list_and_release_exam('gp')
        elif choice == '2':
            list_and_release_exam('nurse')
        elif choice == '3':
            list_and_release_exam('midwife')
        elif choice == '4':
            list_and_release_exam('lab_tech')
        elif choice == '5':
            list_and_release_exam('physiotherapist')
        elif choice == '6':
            list_and_release_exam('icu_nurse')
        elif choice == '7':
            list_and_release_exam('emergency_nurse')
        elif choice == '8':
            list_and_release_exam('neonatal_nurse')
        elif choice == '9':
            list_all_exams_for_release()
        else:
            print("❌ Invalid choice. Please enter 0-9")
        
        input("\n Press Enter to continue...")






def unrelease_exam_menu():
    """Sub-menu for unreleasing exams by profession"""
    while True:
        print("\n" + "=" * 50)
        print("⏸️  UNRELEASE EXAM BY PROFESSION")
        print("=" * 50)
        print("1. 👨‍⚕️  Unrelease GP Exam")
        print("2. 👩‍⚕️  Unrelease Nurse Exam") 
        print("3. 🤰  Unrelease Midwife Exam")
        print("4. 🔬  Unrelease Lab Technologist Exam")
        print("5. 💪  Unrelease Physiotherapist Exam")
        print("6. 🏥  Unrelease ICU Nurse Exam")
        print("7. 🚑  Unrelease Emergency Nurse Exam")
        print("8. 👶  Unrelease Neonatal Nurse Exam")
        print("9. 📋  List all exams with IDs")
        print("0. ↩️  Back to Main Menu")
        print("=" * 50)
        
        choice = input("\nEnter your choice (0-9): ").strip()
        
        if choice == '0':
            break
        elif choice == '1':
            list_and_unrelease_exam('gp')
        elif choice == '2':
            list_and_unrelease_exam('nurse')
        elif choice == '3':
            list_and_unrelease_exam('midwife')
        elif choice == '4':
            list_and_unrelease_exam('lab_tech')
        elif choice == '5':
            list_and_unrelease_exam('physiotherapist')
        elif choice == '6':
            list_and_unrelease_exam('icu_nurse')
        elif choice == '7':
            list_and_unrelease_exam('emergency_nurse')
        elif choice == '8':
            list_and_unrelease_exam('neonatal_nurse')
        elif choice == '9':
            list_all_exams_for_unrelease()
        else:
            print("❌ Invalid choice. Please enter 0-9")
        
        input("\n Press Enter to continue...")



def list_all_exams_for_release():
    """List all exams with IDs for release selection"""
    print("\n📋 ALL EXAMS AVAILABLE FOR RELEASE")
    print("=" * 50)
    
    exams = debug_list_all_exams_with_ids()
    if exams:
        exam_id = input("\nEnter exam ID to release: ").strip()
        if exam_id:
            release_exam(exam_id)
        else:
            print("❌ Please enter a valid exam ID")

def list_all_exams_for_unrelease():
    """List all exams with IDs for unrelease selection"""
    print("\n📋 ALL EXAMS AVAILABLE FOR UNRELEASE")
    print("=" * 50)
    
    exams = debug_list_all_exams_with_ids()
    if exams:
        exam_id = input("\nEnter exam ID to unrelease: ").strip()
        if exam_id:
            unrelease_exam(exam_id)
        else:
            print("❌ Please enter a valid exam ID")

def list_and_release_exam(discipline):
    """List exams for a discipline and allow releasing by list number"""
    print(f"\n🎯 EXAMS FOR {discipline.upper()} - SELECT TO RELEASE")
    print("=" * 50)
    
    exams = list_exams_by_discipline(discipline)
    if exams:
        try:
            choice = input(f"\nEnter list number to release (1-{len(exams)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(exams):
                exam_id = exams[choice_num - 1]['id']
                release_exam(exam_id)
            else:
                print(f"❌ Please enter a number between 1-{len(exams)}")
        except ValueError:
            print("❌ Please enter a valid number")




def list_and_unrelease_exam(discipline):
    """List exams for a discipline and allow unreleasing by list number"""
    print(f"\n🎯 EXAMS FOR {discipline.upper()} - SELECT TO UNRELEASE")
    print("=" * 50)
    
    exams = list_exams_by_discipline(discipline)
    if exams:
        try:
            choice = input(f"\nEnter list number to unrelease (1-{len(exams)}): ").strip()
            choice_num = int(choice)
            if 1 <= choice_num <= len(exams):
                exam_id = exams[choice_num - 1]['id']
                unrelease_exam(exam_id)
            else:
                print(f"❌ Please enter a number between 1-{len(exams)}")
        except ValueError:
            print("❌ Please enter a valid number")



def release_exam(exam_id):
    """Release a specific exam - REPLACE existing released exams with same name"""
    print(f"\n🚀 RELEASING EXAM: {exam_id}")
    print("=" * 50)
    
    try:
        # FIRST: Get the exam details to check for duplicates
        response = requests.get(f"{API_URL}/admin/exams")
        if response.status_code == 200:
            all_exams = response.json()
            current_exam = next((e for e in all_exams if e['id'] == exam_id), None)
            
            if not current_exam:
                print(f"❌ Exam {exam_id} not found")
                return False
            
            # Check for exams with same title that are already released
            duplicate_exams = [
                e for e in all_exams 
                if e['title'] == current_exam['title'] 
                and e['id'] != exam_id 
                and e['is_released']
            ]
            
            if duplicate_exams:
                print(f"⚠️  DUPLICATE RELEASED EXAM FOUND!")
                print(f"   New exam: {current_exam['title']} (ID: {exam_id})")
                for dup in duplicate_exams:
                    print(f"   Already released: {dup['title']} (ID: {dup['id']}) - Released: {dup['release_date']}")
                
                # Ask for confirmation to REPLACE
                choice = input(f"\nReplace the existing released exam with the new one? (y/n): ").strip().lower()
                if choice in ['y', 'yes']:
                    # Unrelease the duplicate exams
                    for dup in duplicate_exams:
                        print(f"🗑️  Unreleasing duplicate: {dup['title']}...")
                        unrelease_response = requests.post(f"{API_URL}/admin/exams/{dup['id']}/unrelease")
                        if unrelease_response.status_code == 200:
                            print(f"✅ Unreleased: {dup['title']}")
                        else:
                            print(f"❌ Failed to unrelease: {dup['title']}")
                else:
                    print("⏭️  Skipping release - keeping existing exam")
                    return False
        
        # NOW release the exam (either no duplicates or user confirmed replacement)
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

 # =====  RELEASE ALL UN RELEASED EXAM FUNCTIONS =====       

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


# ===== NEW: DELETE EXAM FUNCTIONS =====

def delete_specific_exam():
    """Delete a specific exam completely from the system"""
    exam_id = input("Enter exam ID to DELETE: ").strip()
    if not exam_id:
        print("Please enter a valid exam ID")
        return
    
    # Double confirmation
    confirm = input("TYPE 'DELETE' to confirm permanent deletion: ").strip()
    if confirm != 'DELETE':
        print("Deletion cancelled")
        return
    
    try:
        response = requests.delete(f"{API_URL}/admin/exams/{exam_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"SUCCESS: {result['msg']}")
            return True
        else:
            print(f"FAILED: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False




















# ===== NEW: DELETE ALL EXAM FUNCTIONS =====

# def delete_all_exams_in_discipline():
  #  """Delete all exams in a specific discipline"""
   # discipline = input("Enter discipline to delete (gp, nurse, etc): ").strip().lower()
  #  if not discipline:
 #       print("Please enter a valid discipline")
  #      return
    
    # Double confirmation
 #   confirm = input(f"TYPE 'DELETE {discipline.upper()}' to confirm: ").strip()
  #  if confirm != f'DELETE {discipline.upper()}':
   #     print("Deletion cancelled")
  #      return
    
  #  try:
  #      response = requests.delete(f"{API_URL}/admin/exam/discipline/{discipline}")
        
   #     if response.status_code == 200:
   #         result = response.json()
   #         print(f"SUCCESS: {result['msg']}")
   #         return True
    #    else:
    #        print(f"FAILED: {response.status_code} - {response.text}")
    #        return False
            
  #  except Exception as e:
   #     print(f"Error: {e}")
    #    return False



# ===== NEW: DELETE SPECIFIC NOTE FUNCTIONS =====


def delete_specific_note(note_id):
    """Delete a specific note completely from the system"""
    if not note_id:
        print("Please enter a valid note ID")
        return
    
    # Double confirmation
    confirm = input("TYPE 'DELETE' to confirm permanent deletion: ").strip()
    if confirm != 'DELETE':
        print("Deletion cancelled")
        return
    
    try:
        response = requests.delete(f"{API_URL}/admin/exam/{note_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"SUCCESS: {result['msg']}")
            return True
        else:
            print(f"FAILED: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False



# ===== NEW: DELETE ALL EXAM FUNCTIONS =====

def delete_all_exams_in_discipline():
    """Delete all exams in a specific discipline"""
    discipline = input("Enter discipline to delete (gp, nurse, etc): ").strip().lower()
    if not discipline:
        print("Please enter a valid discipline")
        return
    
    # Double confirmation
    confirm = input(f"TYPE 'DELETE {discipline.upper()}' to confirm: ").strip()
    if confirm != f'DELETE {discipline.upper()}':
        print("Deletion cancelled")
        return
    
    try:
        response = requests.delete(f"{API_URL}/admin/exams/discipline/{discipline}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"SUCCESS: {result['msg']}")
            return True
        else:
            print(f"FAILED: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False





def manage_study_notes():
    """Manage study notes (singular exams)"""
    print("\n📚 STUDY NOTES MANAGEMENT")
    print("=" * 50)
    
    while True:
        print("\n" + "=" * 40)
        print("STUDY NOTES MANAGEMENT")
        print("=" * 40)
        print("1. 📋 List all study notes")
        print("2. 🚀 Release a study note")
        print("3. ⏸️  Unrelease a study note")
        print("4. 🗑️  Delete a specific study note")
        print("5. 🗑️  Delete all study notes in discipline")
        print("6. ↩️  Back to main menu")
        print("=" * 40)
        
        choice = input("Enter choice (1-6): ").strip()
        
        if choice == '1':
            # Use the working admin endpoint
            try:
                response = requests.get(f"{API_URL}/admin/exams")
                if response.status_code == 200:
                    all_exams = response.json()
                    # Filter for study notes (singular exams)
                    notes = [exam for exam in all_exams if exam.get('source') == 'singular']
                    print(f"\n📚 Found {len(notes)} study notes:")
                    
                    # Group by discipline
                    by_discipline = {}
                    for note in notes:
                        discipline = note.get('discipline_id', 'unknown')
                        if discipline not in by_discipline:
                            by_discipline[discipline] = []
                        by_discipline[discipline].append(note)
                    
                    # Display by discipline
                    for discipline, discipline_notes in by_discipline.items():
                        print(f"\n🏥 {discipline.upper()} ({len(discipline_notes)} notes):")
                        for note in discipline_notes:
                            status = "🟢 RELEASED" if note['is_released'] else "🔴 UNRELEASED"
                            print(f"   - {note['title']} (ID: {note['id']}) - {status}")
                            
                else:
                    print(f"❌ Failed to fetch: {response.status_code}")
            except Exception as e:
                print(f"💥 Error: {e}")
        
        elif choice == '2':
            note_id = input("Enter note ID to release: ").strip()
            if note_id:
                release_exam(note_id)
        
        elif choice == '3':
            note_id = input("Enter note ID to unrelease: ").strip()
            if note_id:
                unrelease_exam(note_id)
        
        elif choice == '4':
            note_id = input("Enter note ID to delete: ").strip()
            if note_id:
                           
                delete_specific_note(note_id)  # ← CORRECT - pass the note_id
        
        elif choice == '5':
            delete_all_exams_in_discipline()
        
        elif choice == '6':
            break
        
        else:
            print("❌ Invalid choice")
        
        input("\nPress Enter to continue...")








def show_menu():
    """Display admin menu"""
    print("\n" + "=" * 60)
    print("🎛️  EXAM ADMIN CONTROL PANEL")
    print("=" * 60)
    print("1. 📋 List exams by profession")
    print("2. 📚 List notes by profession")
    print("3. 🚀 Release exam by profession")  # UPDATED
    print("4. ⏸️  Unrelease exam by profession")  # UPDATED
    # REMOVED Options 5 & 6 (redundant)
    print("5. 📊 System statistics")  # Changed from 7 to 5
    print("6. 🔄 COMPARE DATABASES")  # Changed from 8 to 6
    print("=" * 60)
    print("👥 USER-SPECIFIC EXAM MANAGEMENT")
    print("=" * 60)
    print("7. 👥 List all users")  # Changed from 9 to 7
    print("8. 👤 Manage exams for specific user")  # Changed from 10 to 8
    print("9. ➕ Grant exam to multiple users")  # Changed from 11 to 9
    print("10. 🔍 Check user's exam access")  # Changed from 12 to 10
    print("=" * 60)
    print("🗑️  DELETE EXAMS")
    print("=" * 60)
    print("11. 🗑️ Delete specific exam")  # Changed from 13 to 11
    print("12. 🗑️ Delete all exams in discipline")  # Changed from 14 to 12
    print("=" * 60)
    print("📚 STUDY NOTES MANAGEMENT")
    print("=" * 60)
    print("13. 📚 Manage study notes")  # Changed from 15 to 13
    print("=" * 60)
    print("14. 🚪 Exit")  # Changed from 16 to 14
    print("=" * 60)


def main():
    """Main admin control loop"""
    print("🔐 Welcome to Exam Admin Control Panel")
    
    while True:
        show_menu()
        choice = input("\nEnter your choice (1-14): ").strip()  # Changed to 14
        
        if choice == '1':
            list_exams_menu()
        
        elif choice == '2':
            list_notes_menu()
        
        elif choice == '3':  # UPDATED
            release_exam_menu()
        
        elif choice == '4':  # UPDATED
            unrelease_exam_menu()
        
        elif choice == '5':  # Changed from 7 to 5
            get_system_stats()
        
        elif choice == '6':  # Changed from 8 to 6
            compare_databases()
        
        # USER-SPECIFIC FUNCTIONS
        elif choice == '7':  # Changed from 9 to 7
            list_all_users()
        
        elif choice == '8':  # Changed from 10 to 8
            manage_user_specific_exams()
        
        elif choice == '9':  # Changed from 11 to 9
            grant_exam_to_multiple_users()
        
        elif choice == '10':  # Changed from 12 to 10
            user_id = input("Enter user ID to check access: ").strip()
            if user_id:
                get_user_exam_access(user_id)
        
        elif choice == '11':  # Changed from 13 to 11
            delete_specific_exam()
        
        elif choice == '12':  # Changed from 14 to 12
            delete_all_exams_in_discipline()
        
        elif choice == '13':  # Changed from 15 to 13
            manage_study_notes()
        
        elif choice == '14':  # Changed from 16 to 14
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")












if __name__ == "__main__":
    try:
        print("🔍 Testing imports...")
        import requests
        import json
        from datetime import datetime
        import sqlite3
        import os
        print("✅ All imports successful")
        
        print("🔍 Testing function definitions...")
        # Test if all required functions exist
        required_functions = [
            'list_exams_menu', 'list_notes_menu', 'release_exam', 'unrelease_exam',
            'release_all_unreleased', 'get_system_stats', 'compare_databases',
            'list_all_users', 'manage_user_specific_exams', 'grant_exam_to_multiple_users',
            'get_user_exam_access', 'delete_specific_exam', 'delete_all_exams_in_discipline',
            'manage_study_notes', 'list_all_exams', 'list_exams_by_discipline',
            'list_all_notes', 'list_notes_by_discipline', 'grant_exam_access_to_user',
            'revoke_exam_access_from_user', 'debug_list_all_exams_with_ids'
        ]
        
        missing_functions = []
        for func in required_functions:
            if func not in globals():
                missing_functions.append(func)
        
        if missing_functions:
            print(f"❌ MISSING FUNCTIONS: {missing_functions}")
            input("Press Enter to exit...")
        else:
            print("✅ All functions defined")
            print("🚀 Starting main program...")
            main()
            
    except Exception as e:
        print(f"💥 STARTUP ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")

        