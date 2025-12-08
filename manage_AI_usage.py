#!/usr/bin/env python3
"""
AI USAGE MANAGEMENT SYSTEM
- Shows proper profession labels
- 6-digit unique user IDs
- Profession-based management
"""

import sqlite3
import json
import sys
import os
from datetime import datetime

# ========== PROFESSION MAPPING ==========
PROFESSION_MAP = {
    'gp': 'General Practitioner',
    'nurse': 'General Nurse',
    'midwife': 'Midwife',
    'lab_tech': 'Lab Technologist',
    'physiotherapist': 'Physiotherapist',
    'icu_nurse': 'ICU Nurse',
    'emergency_nurse': 'Emergency Nurse',
    'neonatal_nurse': 'Neonatal Nurse',
    'admin': 'System Administrator',
    'specialist_nurse': 'Specialist Nurse'
}

def get_profession_label(db_value):
    """Convert database profession value to display label"""
    return PROFESSION_MAP.get(db_value, db_value.upper())

def get_profession_value(label):
    """Convert display label back to database value"""
    reverse_map = {v.lower(): k for k, v in PROFESSION_MAP.items()}
    return reverse_map.get(label.lower(), label.lower())

# ========== DATABASE FUNCTIONS ==========

def get_db_connection():
    """Connect to database"""
    db_file = "theclamed.db"
    if not os.path.exists(db_file):
        print(f"❌ Database file '{db_file}' not found!")
        return None
    
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return None

def ensure_unique_ids():
    """Ensure all users have 6-digit unique IDs"""
    conn = get_db_connection()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    # Check if unique_id column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'unique_id' not in columns:
        print("➕ Adding unique_id column...")
        cursor.execute("ALTER TABLE users ADD COLUMN unique_id VARCHAR(6)")
        conn.commit()
    
    # Check for users without unique IDs
    cursor.execute("SELECT COUNT(*) FROM users WHERE unique_id IS NULL")
    missing = cursor.fetchone()[0]
    
    if missing > 0:
        print(f"🆔 Generating unique IDs for {missing} users...")
        
        # Generate unique IDs
        import random
        import string
        
        cursor.execute("SELECT id, email FROM users WHERE unique_id IS NULL")
        users = cursor.fetchall()
        
        existing_ids = set()
        cursor.execute("SELECT unique_id FROM users WHERE unique_id IS NOT NULL")
        for (uid,) in cursor.fetchall():
            existing_ids.add(uid)
        
        for user_id, email in users:
            while True:
                # Generate 6-digit alphanumeric ID
                new_id = ''.join(random.choices(
                    string.ascii_uppercase + string.digits, k=6
                ))
                if new_id not in existing_ids:
                    existing_ids.add(new_id)
                    break
            
            cursor.execute(
                "UPDATE users SET unique_id = ? WHERE id = ?",
                (new_id, user_id)
            )
            print(f"  ✅ {email[:25]:25s} → {new_id}")
        
        conn.commit()
        print(f"\n🎯 Generated IDs for {missing} users")
    
    conn.close()
    return True

# ========== DISPLAY FUNCTIONS ==========

def list_professions_menu():
    """Show numbered list of professions with proper labels"""
    conn = get_db_connection()
    if not conn:
        return None
    
    cursor = conn.cursor()
    
    # Get all professions with user counts
    cursor.execute("""
        SELECT DISTINCT profession, COUNT(*) as user_count
        FROM users 
        WHERE status = 'approved'
        GROUP BY profession
        ORDER BY profession
    """)
    
    professions = cursor.fetchall()
    conn.close()
    
    if not professions:
        print("❌ No approved users found")
        return None
    
    print("\n" + "="*60)
    print("📚 AVAILABLE PROFESSIONS")
    print("="*60)
    
    profession_map = {}  # Maps menu number to database value
    profession_labels = {}  # Maps database value to display label
    
    for idx, (profession, count) in enumerate(professions, 1):
        profession_map[idx] = profession
        label = get_profession_label(profession)
        profession_labels[profession] = label
        print(f"{idx:2d}. {label:25s} ({count} users)")
    
    print("="*60)
    return profession_map, profession_labels

def list_users_in_profession(profession_db_value, profession_label):
    """List all users in a specific profession"""
    conn = get_db_connection()
    if not conn:
        return []
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT unique_id, email, full_name, premium_features
        FROM users 
        WHERE profession = ? AND status = 'approved'
        ORDER BY email
    """, (profession_db_value,))
    
    users = cursor.fetchall()
    conn.close()
    
    if not users:
        print(f"\n❌ No {profession_label} users found")
        return []
    
    print(f"\n" + "="*70)
    print(f"👥 {profession_label.upper()} USERS ({len(users)} users)")
    print("="*70)
    
    for uid, email, name, premium_json in users:
        # Parse premium status
        try:
            premium = json.loads(premium_json) if premium_json else {}
            is_premium = premium.get('ai_simulation', False)
            status = "🟢 PREMIUM" if is_premium else "🔵 BASIC"
            
            # Show custom limits if any
            custom_limits = premium.get('custom_limits', {})
            limits_text = ""
            if custom_limits:
                sim = custom_limits.get('simulations_per_day', 'default')
                proc = custom_limits.get('procedures_per_day', 'default')
                quiz = custom_limits.get('quiz_questions_per_day', 'default')
                limits_text = f" | S={sim}, P={proc}, Q={quiz}"
            
        except:
            status = "⚪ UNKNOWN"
            limits_text = ""
        
        print(f"  {uid} | {email:30s} | {name:20s} | {status}{limits_text}")
    
    print("="*70)
    return users

def show_user_details(user_id):
    """Show detailed information about a user"""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT email, full_name, profession, premium_features, created_at
        FROM users 
        WHERE unique_id = ?
    """, (user_id,))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        print(f"❌ User {user_id} not found")
        return
    
    email, name, profession_db, premium_json, created_at = user
    profession_label = get_profession_label(profession_db)
    
    # Parse premium features
    try:
        premium = json.loads(premium_json) if premium_json else {}
        is_premium = premium.get('ai_simulation', False)
        custom_limits = premium.get('custom_limits', {})
    except:
        premium = {}
        is_premium = False
        custom_limits = {}
    
    print(f"\n" + "="*60)
    print(f"📋 USER DETAILS: {user_id}")
    print("="*60)
    print(f"ID:         {user_id}")
    print(f"Email:      {email}")
    print(f"Name:       {name}")
    print(f"Profession: {profession_label}")
    print(f"Created:    {created_at[:10]}")
    print(f"Status:     {'🟢 PREMIUM' if is_premium else '🔵 BASIC'}")
    
    if custom_limits:
        print(f"\n⚙️ CUSTOM LIMITS:")
        print(f"  Simulations/day: {custom_limits.get('simulations_per_day', 'default')}")
        print(f"  Procedures/day:  {custom_limits.get('procedures_per_day', 'default')}")
        print(f"  Quiz Qs/day:     {custom_limits.get('quiz_questions_per_day', 'default')}")
        if 'updated_at' in custom_limits:
            print(f"  Last updated:   {custom_limits['updated_at'][:19]}")
    
    print("="*60)

# ========== MANAGEMENT FUNCTIONS ==========

def set_user_limits(user_id):
    """Set custom limits for a specific user"""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Get user details
    cursor.execute("SELECT email FROM users WHERE unique_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if not result:
        print(f"❌ User {user_id} not found")
        conn.close()
        return
    
    email = result[0]
    
    print(f"\n🎯 Setting limits for: {email}")
    print("   (Enter numbers, 0 = unlimited, empty = no change)")
    
    # Get current limits
    cursor.execute("SELECT premium_features FROM users WHERE unique_id = ?", (user_id,))
    premium_json = cursor.fetchone()[0]
    
    try:
        premium = json.loads(premium_json) if premium_json else {}
        current_limits = premium.get('custom_limits', {})
    except:
        premium = {}
        current_limits = {}
    
    # Get new limits with better prompts
    print("\nCurrent limits in brackets:")
    sim = input(f"  Simulations per day [{current_limits.get('simulations_per_day', 'default')}]: ").strip()
    proc = input(f"  Procedures per day [{current_limits.get('procedures_per_day', 'default')}]: ").strip()
    quiz = input(f"  Quiz questions/day [{current_limits.get('quiz_questions_per_day', 'default')}]: ").strip()
    
    if not sim and not proc and not quiz:
        print("⚠️ No changes made")
        conn.close()
        return
    
    # Update limits
    if 'custom_limits' not in premium:
        premium['custom_limits'] = {}
    
    if sim:
        premium['custom_limits']['simulations_per_day'] = int(sim)
    if proc:
        premium['custom_limits']['procedures_per_day'] = int(proc)
    if quiz:
        premium['custom_limits']['quiz_questions_per_day'] = int(quiz)
    
    premium['custom_limits']['updated_at'] = datetime.now().isoformat()
    premium['custom_limits']['updated_by'] = 'admin_tool'
    
    # Save to database
    cursor.execute(
        "UPDATE users SET premium_features = ? WHERE unique_id = ?",
        (json.dumps(premium), user_id)
    )
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Limits updated for {email}")

def set_profession_limits(profession_db_value, profession_label):
    """Set limits for all users in a profession"""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Count users in profession
    cursor.execute("SELECT COUNT(*) FROM users WHERE profession = ?", (profession_db_value,))
    count = cursor.fetchone()[0]
    
    if count == 0:
        print(f"❌ No {profession_label} users found")
        conn.close()
        return
    
    print(f"\n🎯 Setting limits for ALL {profession_label} users ({count} users)")
    print("   (Enter numbers, 0 = unlimited)")
    
    sim = input("Simulations per day: ").strip()
    proc = input("Procedures per day: ").strip()
    quiz = input("Quiz questions per day: ").strip()
    
    if not sim and not proc and not quiz:
        print("⚠️ No limits provided")
        conn.close()
        return
    
    # Get all users
    cursor.execute("SELECT unique_id, email FROM users WHERE profession = ?", (profession_db_value,))
    users = cursor.fetchall()
    
    updated = 0
    for uid, email in users:
        # Get current premium features
        cursor.execute("SELECT premium_features FROM users WHERE unique_id = ?", (uid,))
        result = cursor.fetchone()
        
        if result:
            premium_json = result[0]
            try:
                premium = json.loads(premium_json) if premium_json else {}
            except:
                premium = {}
            
            if 'custom_limits' not in premium:
                premium['custom_limits'] = {}
            
            # Update limits
            if sim:
                premium['custom_limits']['simulations_per_day'] = int(sim)
            if proc:
                premium['custom_limits']['procedures_per_day'] = int(proc)
            if quiz:
                premium['custom_limits']['quiz_questions_per_day'] = int(quiz)
            
            premium['custom_limits']['updated_at'] = datetime.now().isoformat()
            premium['custom_limits']['updated_by'] = 'admin_tool'
            
            # Save
            cursor.execute(
                "UPDATE users SET premium_features = ? WHERE unique_id = ?",
                (json.dumps(premium), uid)
            )
            updated += 1
    
    conn.commit()
    conn.close()
    print(f"\n✅ Updated {updated} {profession_label} users")

def upgrade_user(user_id, to_premium=True):
    """Upgrade or downgrade a user"""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Get user email
    cursor.execute("SELECT email FROM users WHERE unique_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if not result:
        print(f"❌ User {user_id} not found")
        conn.close()
        return
    
    email = result[0]
    
    # Get current premium features
    cursor.execute("SELECT premium_features FROM users WHERE unique_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if not result or not result[0]:
        premium_json = '{}'
    else:
        premium_json = result[0]
    
    try:
        premium = json.loads(premium_json) if premium_json else {}
    except:
        premium = {}
    
    if to_premium:
        # Upgrade to premium
        premium.update({
            'ai_simulation': True,
            'procedure_trainer': True,
            'unlimited_quizzes': True,
            'advanced_analytics': True
        })
        action = "upgraded to PREMIUM"
    else:
        # Downgrade to basic
        premium.update({
            'ai_simulation': False,
            'procedure_trainer': False,
            'unlimited_quizzes': False,
            'advanced_analytics': False
        })
        action = "downgraded to BASIC"
    
    # Save
    cursor.execute(
        "UPDATE users SET premium_features = ? WHERE unique_id = ?",
        (json.dumps(premium), user_id)
    )
    
    conn.commit()
    conn.close()
    print(f"✅ {email} {action}")

# ========== MENU FUNCTIONS ==========

def profession_submenu(profession_db_value, profession_label):
    """Submenu after selecting a profession"""
    while True:
        print(f"\n🎯 ACTIONS for {profession_label.upper()}:")
        print("1. 📝 Set limits for ALL users")
        print("2. ⬆️  Upgrade ALL users to premium")
        print("3. ⬇️  Downgrade ALL users to basic")
        print("4. 👤 Manage specific user")
        print("5. 📋 Show user list again")
        print("6. ↩️  Back to main menu")
        
        choice = input("\nSelect (1-6): ").strip()
        
        if choice == "1":
            set_profession_limits(profession_db_value, profession_label)
        elif choice == "2":
            confirm = input(f"Upgrade ALL {profession_label} users to premium? (y/n): ").strip().lower()
            if confirm == 'y':
                bulk_upgrade_profession(profession_db_value, profession_label, to_premium=True)
        elif choice == "3":
            confirm = input(f"Downgrade ALL {profession_label} users to basic? (y/n): ").strip().lower()
            if confirm == 'y':
                bulk_upgrade_profession(profession_db_value, profession_label, to_premium=False)
        elif choice == "4":
            user_id = input(f"Enter {profession_label} user ID: ").strip().upper()
            if len(user_id) == 6:
                user_submenu(user_id)
            else:
                print("❌ User ID must be 6 characters")
        elif choice == "5":
            list_users_in_profession(profession_db_value, profession_label)
        elif choice == "6":
            break
        else:
            print("❌ Invalid choice")

def bulk_upgrade_profession(profession_db_value, profession_label, to_premium=True):
    """Bulk upgrade/downgrade all users in a profession"""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Get all users
    cursor.execute("SELECT unique_id, email FROM users WHERE profession = ?", (profession_db_value,))
    users = cursor.fetchall()
    
    updated = 0
    for uid, email in users:
        # Get current premium features
        cursor.execute("SELECT premium_features FROM users WHERE unique_id = ?", (uid,))
        result = cursor.fetchone()
        
        if result:
            premium_json = result[0]
            try:
                premium = json.loads(premium_json) if premium_json else {}
            except:
                premium = {}
            
            if to_premium:
                premium.update({
                    'ai_simulation': True,
                    'procedure_trainer': True,
                    'unlimited_quizzes': True,
                    'advanced_analytics': True
                })
            else:
                premium.update({
                    'ai_simulation': False,
                    'procedure_trainer': False,
                    'unlimited_quizzes': False,
                    'advanced_analytics': False
                })
            
            # Save
            cursor.execute(
                "UPDATE users SET premium_features = ? WHERE unique_id = ?",
                (json.dumps(premium), uid)
            )
            updated += 1
    
    conn.commit()
    conn.close()
    
    action = "upgraded" if to_premium else "downgraded"
    print(f"✅ {action.capitalize()} {updated} {profession_label} users")

def user_submenu(user_id):
    """Submenu for managing a specific user"""
    show_user_details(user_id)
    
    while True:
        print(f"\n⚙️ ACTIONS for user {user_id}:")
        print("1. 📝 Set custom limits")
        print("2. ⬆️  Upgrade to premium")
        print("3. ⬇️  Downgrade to basic")
        print("4. 📋 Show details again")
        print("5. ↩️  Back to profession menu")
        
        choice = input("\nSelect (1-5): ").strip()
        
        if choice == "1":
            set_user_limits(user_id)
        elif choice == "2":
            upgrade_user(user_id, to_premium=True)
        elif choice == "3":
            upgrade_user(user_id, to_premium=False)
        elif choice == "4":
            show_user_details(user_id)
        elif choice == "5":
            break
        else:
            print("❌ Invalid choice")

def main_menu():
    """Main menu loop"""
    # Ensure unique IDs exist
    if not ensure_unique_ids():
        print("❌ Cannot proceed without database")
        return
    
    while True:
        print("\n" + "="*60)
        print("🤖 AI USAGE MANAGEMENT SYSTEM")
        print("="*60)
        print("\n📋 MAIN MENU:")
        print("1. 📚 List users by profession")
        print("2. 👤 Manage specific user by ID")
        print("3. 🚪 Exit")
        
        choice = input("\nSelect (1-3): ").strip()
        
        if choice == "1":
            # List professions
            result = list_professions_menu()
            if not result:
                continue
            
            profession_map, profession_labels = result
            
            try:
                prof_choice = int(input("\nSelect profession (number): "))
                
                if prof_choice not in profession_map:
                    print("❌ Invalid choice")
                    continue
                
                profession_db_value = profession_map[prof_choice]
                profession_label = profession_labels[profession_db_value]
                
                list_users_in_profession(profession_db_value, profession_label)
                profession_submenu(profession_db_value, profession_label)
                
            except ValueError:
                print("❌ Please enter a valid number")
        
        elif choice == "2":
            user_id = input("Enter 6-digit user ID: ").strip().upper()
            if len(user_id) != 6:
                print("❌ User ID must be 6 characters")
                continue
            
            user_submenu(user_id)
        
        elif choice == "3":
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")

# ========== MAIN ==========

if __name__ == "__main__":
    print("\n" + "="*60)
    print("⚡ AI USAGE MANAGEMENT SYSTEM")
    print("="*60)
    print("📊 Shows proper profession labels")
    print("🆔 Uses 6-digit unique user IDs")
    print("🎯 Profession-based management")
    print("="*60)
    
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")