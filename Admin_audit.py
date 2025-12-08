#!/usr/bin/env python3
"""
Working Admin Tool for FastAPI Backend
Using discovered endpoints
"""

import requests
import json
import sys
import os
from datetime import datetime, date
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class AdminTool:
    def __init__(self):
        #self.base_url = os.getenv("BASE_URL", "https://2589fc685327.ngrok-free.app")
        self.base_url = os.getenv("BASE_URL", "https://thecla-backend.onrender.com")

        self.username = os.getenv("ADMIN_USERNAME", "")
        self.password = os.getenv("ADMIN_PASSWORD", "")
        self.token = None
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    def login(self) -> bool:
        """Login to get admin token"""
        print(f"\n🔐 Logging in as {self.username}...")
        
        try:
            response = self.session.post(
                f"{self.base_url}/login",
                json={
                    "username": self.username,
                    "password": self.password
                },
                timeout=10
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("   ✅ Login successful!")
                
                # Extract token (try common field names)
                token_fields = ['access_token', 'accessToken', 'token']
                for field in token_fields:
                    if field in data:
                        self.token = data[field]
                        print(f"   Token found in '{field}' field")
                        break
                
                if not self.token and 'access_token' in data:
                    self.token = data['access_token']
                
                if self.token:
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.token}"
                    })
                    return True
                else:
                    print("   ⚠️  No token found in response")
                    print(f"   Response keys: {list(data.keys())}")
                    # Maybe token is in a nested structure
                    if 'data' in data and isinstance(data['data'], dict):
                        for field in token_fields:
                            if field in data['data']:
                                self.token = data['data'][field]
                                print(f"   Token found in data.{field}")
                                self.session.headers.update({
                                    "Authorization": f"Bearer {self.token}"
                                })
                                return True
                    return False
                    
            elif response.status_code == 422:
                print("   ❌ Validation error - check username/password format")
                error_detail = response.json().get('detail', [{}])[0]
                print(f"   Error: {error_detail.get('msg', 'Unknown')}")
                return False
            elif response.status_code == 401:
                print("   ❌ Unauthorized - invalid credentials")
                return False
            else:
                print(f"   ❌ Login failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"   ❌ Connection error: {e}")
            return False
    
    def get_all_users(self) -> List[Dict]:
        """Get all users from /admin/users endpoint"""
        print("\n👥 Getting all users...")
        
        try:
            response = self.session.get(
                f"{self.base_url}/admin/users",
                timeout=10
            )
            
            if response.status_code == 200:
                users = response.json()
                print(f"   ✅ Found {len(users)} users")
                return users
            elif response.status_code == 401:
                print("   🔒 Unauthorized - invalid or expired token")
                return []
            elif response.status_code == 403:
                print("   ⛔ Forbidden - admin privileges required")
                return []
            else:
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return []
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return []
    
    def get_user_details(self, user_id: int) -> Optional[Dict]:
        """Get detailed user information"""
        print(f"\n📋 Getting details for user {user_id}...")
        
        # Try different endpoint patterns
        endpoints = [
            f"/admin/users/{user_id}",
            f"/api/admin/users/{user_id}",
            f"/users/{user_id}"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(
                    f"{self.base_url}{endpoint}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    user = response.json()
                    print(f"   ✅ Found user via {endpoint}")
                    return user
                elif response.status_code == 404:
                    continue  # Try next endpoint
                    
            except Exception as e:
                print(f"   Error with {endpoint}: {e}")
        
        print(f"   ❌ User {user_id} not found")
        return None
    
    def upgrade_to_premium(self, user_id: int, duration_days: int = 30) -> bool:
        """Upgrade user to premium"""
        print(f"\n⬆️  Upgrading user {user_id} to Premium ({duration_days} days)...")
        
        # Try different endpoint patterns
        endpoints = [
            f"/admin/users/{user_id}/upgrade-to-premium",
            f"/api/admin/users/{user_id}/upgrade",
            f"/admin/upgrade-user/{user_id}"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.post(
                    f"{self.base_url}{endpoint}",
                    json={"duration_days": duration_days, "notes": "Admin tool upgrade"},
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    print(f"   ✅ Upgraded via {endpoint}")
                    print(f"   Response: {response.json()}")
                    return True
                elif response.status_code == 404:
                    continue  # Try next endpoint
                    
            except Exception as e:
                print(f"   Error with {endpoint}: {e}")
        
        # If no upgrade endpoint, we can update via PUT /admin/users/{id}
        print("   ⚠️  No direct upgrade endpoint, trying to update user directly...")
        
        user = self.get_user_details(user_id)
        if not user:
            return False
        
        # Prepare update data
        update_data = {
            "is_premium": True,
            "subscription_end_date": (datetime.now() + datetime.timedelta(days=duration_days)).isoformat()
        }
        
        try:
            response = self.session.put(
                f"{self.base_url}/admin/users/{user_id}",
                json=update_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                print("   ✅ User updated to premium")
                return True
            else:
                print(f"   ❌ Update failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def get_daily_usage(self, target_date: Optional[str] = None) -> Dict:
        """Get daily usage statistics"""
        if not target_date:
            target_date = date.today().isoformat()
        
        print(f"\n📊 Getting daily usage for {target_date}...")
        
        try:
            response = self.session.get(
                f"{self.base_url}/admin/audit/daily-usage/{target_date}",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print("   ✅ Daily usage data retrieved")
                return data
            else:
                print(f"   ❌ Failed: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return {}
    
    def get_user_usage(self, target_date: Optional[str] = None) -> List[Dict]:
        """Get user usage statistics"""
        if not target_date:
            target_date = date.today().isoformat()
        
        print(f"\n📈 Getting user usage for {target_date}...")
        
        try:
            response = self.session.get(
                f"{self.base_url}/admin/audit/user-usage",
                params={"date": target_date},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Found usage data for {len(data)} users")
                return data
            else:
                print(f"   ❌ Failed: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return []
    
    def display_users_table(self, users: List[Dict]):
        """Display users in a nice table"""
        if not users:
            print("\nNo users found")
            return
        
        print("\n" + "="*120)
        print(f"{'ID':<6} {'Username':<20} {'Email':<30} {'Premium':<8} {'Admin':<6} {'Created':<12} {'Last Login':<12}")
        print("="*120)
        
        for user in users:
            user_id = str(user.get('id', user.get('user_id', '')))
            username = str(user.get('username', ''))[:19]
            email = str(user.get('email', ''))[:29]
            
            # Premium status
            is_premium = user.get('is_premium', user.get('premium', False))
            premium_str = "✅" if is_premium else "❌"
            
            # Admin status
            is_admin = user.get('is_admin', user.get('admin', False))
            admin_str = "👑" if is_admin else ""
            
            # Dates
            created = str(user.get('created_at', ''))[:10]
            last_login = str(user.get('last_login', ''))[:10] if user.get('last_login') else 'Never'
            
            print(f"{user_id:<6} {username:<20} {email:<30} {premium_str:<8} {admin_str:<6} {created:<12} {last_login:<12}")
        
        print("="*120)
        print(f"Total users: {len(users)}")
        
        # Count statistics
        premium_count = sum(1 for u in users if u.get('is_premium', u.get('premium', False)))
        admin_count = sum(1 for u in users if u.get('is_admin', u.get('admin', False)))
        
        print(f"Premium users: {premium_count} | Admin users: {admin_count}")
    
    def display_daily_usage(self, data: Dict):
        """Display daily usage statistics"""
        if not data:
            print("No usage data")
            return
        
        print("\n" + "="*60)
        print("DAILY USAGE STATISTICS")
        print("="*60)
        
        date_str = data.get('date', 'Unknown')
        print(f"📅 Date: {date_str}")
        print(f"👥 Active Users: {data.get('total_users', 0)}")
        print(f"   - Premium: {data.get('premium_users', 0)}")
        print(f"   - Basic: {data.get('basic_users', 0)}")
        print(f"📊 Resource Usage:")
        print(f"   🏥 Simulations: {data.get('total_simulations', 0)}")
        print(f"   🩺 Procedures: {data.get('total_procedures', 0)}")
        print(f"   🧠 AI Questions: {data.get('total_quiz_questions', 0)}")
        print("="*60)
    
    def run_interactive(self):
        """Run interactive admin console"""
        print("\n" + "="*60)
        print("ADMIN CONSOLE")
        print("="*60)
        
        # Login
        if not self.login():
            print("\n❌ Login failed. Please check:")
            print(f"   Username: {self.username}")
            print(f"   Password: {'*' * len(self.password) if self.password else 'NOT SET'}")
            print("\n💡 Try setting ADMIN_USERNAME and ADMIN_PASSWORD in .env file")
            return
        
        print(f"\n✅ Logged in successfully!")
        
        while True:
            print("\n" + "="*60)
            print("MAIN MENU")
            print("="*60)
            print("1. 👥 List all users")
            print("2. 📋 View user details")
            print("3. ⬆️  Upgrade user to Premium")
            print("4. 📊 View daily usage")
            print("5. 📈 View user usage details")
            print("6. 🔄 Test other admin endpoints")
            print("7. 🚪 Exit")
            print("="*60)
            
            choice = input("\nSelect option (1-7): ").strip()
            
            if choice == "1":
                users = self.get_all_users()
                self.display_users_table(users)
                
                # Show quick actions
                if users:
                    action = input("\nEnter user ID for details (or press Enter to continue): ").strip()
                    if action.isdigit():
                        self.get_user_details(int(action))
            
            elif choice == "2":
                try:
                    user_id = int(input("Enter user ID: "))
                    user = self.get_user_details(user_id)
                    if user:
                        print(f"\n📋 User Details:")
                        for key, value in user.items():
                            print(f"   {key}: {value}")
                except ValueError:
                    print("Invalid user ID")
            
            elif choice == "3":
                try:
                    user_id = int(input("Enter user ID to upgrade: "))
                    duration = input("Duration in days (default 30): ").strip()
                    duration_days = int(duration) if duration.isdigit() else 30
                    
                    confirm = input(f"Upgrade user {user_id} to Premium for {duration_days} days? (y/n): ").strip().lower()
                    if confirm == 'y':
                        self.upgrade_to_premium(user_id, duration_days)
                except ValueError:
                    print("Invalid input")
            
            elif choice == "4":
                date_input = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
                data = self.get_daily_usage(date_input if date_input else None)
                self.display_daily_usage(data)
            
            elif choice == "5":
                date_input = input("Enter date (YYYY-MM-DD) or press Enter for today: ").strip()
                user_usage = self.get_user_usage(date_input if date_input else None)
                
                if user_usage:
                    print(f"\n📊 User Usage Details:")
                    for usage in user_usage[:10]:  # Show first 10
                        user_id = usage.get('user_id', 'N/A')
                        sim = usage.get('simulations', 0)
                        proc = usage.get('procedures', 0)
                        quiz = usage.get('ai_quiz_questions', usage.get('quiz_questions', 0))
                        print(f"   User {user_id}: Sim={sim}, Proc={proc}, Quiz={quiz}")
                    
                    if len(user_usage) > 10:
                        print(f"   ... and {len(user_usage) - 10} more users")
            
            elif choice == "6":
                print("\n🔧 Testing admin endpoints...")
                # Test other endpoints that might exist
                test_endpoints = [
                    "/admin/health",
                    "/admin/stats",
                    "/admin/dashboard",
                    "/admin/metrics"
                ]
                
                for endpoint in test_endpoints:
                    try:
                        response = self.session.get(f"{self.base_url}{endpoint}", timeout=5)
                        if response.status_code == 200:
                            print(f"✅ {endpoint}: Accessible")
                        elif response.status_code != 404:
                            print(f"⚠️  {endpoint}: Status {response.status_code}")
                    except:
                        pass
            
            elif choice == "7":
                print("\nGoodbye! 👋")
                break
            
            else:
                print("Invalid choice")

def check_env():
    """Check and create .env file if needed"""
    if not os.path.exists(".env"):
        print("⚠️  No .env file found!")
        print("\nCreating .env file...")
        
        with open(".env", "w") as f:
            f.write("# Admin credentials for FastAPI backend\n")
            f.write("BASE_URL=https://2589fc685327.ngrok-free.app\n")
            f.write("# Use the username/password of an existing admin user\n")
            f.write("ADMIN_USERNAME=\n")
            f.write("ADMIN_PASSWORD=\n")
        
        print("✅ Created .env file")
        print("\n⚠️  Please edit .env and add your admin credentials!")
        print("   The username should be for an existing admin user in your database.")
        return False
    
    # Check if credentials are set
    load_dotenv()
    if not os.getenv("ADMIN_USERNAME") or not os.getenv("ADMIN_PASSWORD"):
        print("⚠️  ADMIN_USERNAME or ADMIN_PASSWORD not set in .env file!")
        return False
    
    return True

if __name__ == "__main__":
    print("\n⚡ FastAPI Admin Management Tool")
    print("="*60)
    print("\nFound endpoints on your backend:")
    print("✅ GET /admin/users")
    print("✅ GET /admin/audit/daily-usage/{date}")
    print("✅ GET /admin/audit/user-usage")
    
    if check_env():
        tool = AdminTool()
        tool.run_interactive()