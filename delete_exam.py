import requests
import time

def clear_all_exams_safely():
    """
    Safely delete all exams using only the API endpoints.
    Uses the plural 'exams/' endpoint for listing and deleting.
    """
    API_BASE_URL = 'https://thecla-backend.onrender.com'
    EXAMS_ENDPOINT = f'{API_BASE_URL}/exams/'
    
    print("=" * 60)
    print("🗑️  EXAM DATABASE CLEANUP TOOL")
    print("=" * 60)
    print(f"API URL: {EXAMS_ENDPOINT}")
    print("Database: theclamed.db")
    print("=" * 60)
    
    # First, verify we can connect to the API
    print("🔍 Testing API connection...")
    try:
        test_response = requests.get(EXAMS_ENDPOINT, timeout=10)
        if test_response.status_code != 200:
            print(f"❌ API connection failed. Status: {test_response.status_code}")
            print(f"   Response: {test_response.text[:200]}")
            return False
        print("✅ API connection successful")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to API: {e}")
        return False
    
    # Get all existing exams
    print("\n📋 Fetching all exams from database...")
    try:
        response = requests.get(EXAMS_ENDPOINT, timeout=30)
        
        if response.status_code == 200:
            exams = response.json()
            
            if not exams:
                print("✅ Database is already empty!")
                return True
                
            print(f"📊 Found {len(exams)} exams in the database")
            
            # Show exam summary
            print("\n📋 EXAM SUMMARY:")
            print("-" * 60)
            for i, exam in enumerate(exams, 1):
                exam_id = exam.get('id', 'N/A')
                title = exam.get('title', 'Untitled')
                discipline = exam.get('discipline_id', 'unknown')
                question_count = len(exam.get('questions', []))
                print(f"{i:3d}. {title[:40]:40} | {discipline:15} | {question_count:3d} questions")
            
            print("-" * 60)
            
            # Double confirmation
            print("\n⚠️  ⚠️  ⚠️  WARNING: This action cannot be undone! ⚠️  ⚠️  ⚠️")
            print(f"This will permanently delete ALL {len(exams)} exams.")
            
            confirmation1 = input("\nType 'YES' to continue: ")
            if confirmation1 != "YES":
                print("❌ First confirmation failed. Operation cancelled.")
                return False
                
            confirmation2 = input("Type 'DELETE ALL EXAMS' to confirm again: ")
            if confirmation2 != "DELETE ALL EXAMS":
                print("❌ Second confirmation failed. Operation cancelled.")
                return False
            
            # Delete each exam one by one
            print(f"\n🗑️  Starting deletion of {len(exams)} exams...")
            print("-" * 60)
            
            deleted_count = 0
            failed_deletions = []
            
            for exam in exams:
                exam_id = exam.get('id')
                title = exam.get('title', 'Unknown Exam')
                
                if not exam_id:
                    print(f"❓ Skipping exam without ID: {title}")
                    continue
                
                # Delete using DELETE /exams/{id}
                delete_url = f"{EXAMS_ENDPOINT}{exam_id}"
                
                try:
                    print(f"Deleting: {title[:50]}...", end=" ", flush=True)
                    
                    delete_response = requests.delete(delete_url, timeout=10)
                    
                    if delete_response.status_code == 200:
                        print(f"✅ Deleted")
                        deleted_count += 1
                    else:
                        print(f"❌ Failed (Status: {delete_response.status_code})")
                        failed_deletions.append({
                            'title': title,
                            'id': exam_id,
                            'status': delete_response.status_code,
                            'error': delete_response.text[:100]
                        })
                    
                    # Small delay to avoid overwhelming the server
                    time.sleep(0.1)
                    
                except requests.exceptions.RequestException as e:
                    print(f"❌ Error: {str(e)[:50]}")
                    failed_deletions.append({
                        'title': title,
                        'id': exam_id,
                        'error': str(e)
                    })
            
            # Summary report
            print("\n" + "=" * 60)
            print("📊 CLEANUP COMPLETE - SUMMARY")
            print("=" * 60)
            print(f"✅ Successfully deleted: {deleted_count}/{len(exams)} exams")
            
            if failed_deletions:
                print(f"❌ Failed to delete: {len(failed_deletions)} exams")
                print("\nFailed exams:")
                for fail in failed_deletions:
                    print(f"  - {fail['title'][:40]:40} | ID: {fail['id'][:8]}... | Error: {fail.get('error', 'Unknown')[:50]}")
            
            # Verify database is empty
            print("\n🔍 Verifying database is empty...")
            verify_response = requests.get(EXAMS_ENDPOINT, timeout=10)
            if verify_response.status_code == 200:
                remaining_exams = verify_response.json()
                if not remaining_exams:
                    print("✅ Verification passed: Database is now empty!")
                else:
                    print(f"⚠️  Database still has {len(remaining_exams)} exams remaining")
            
            print("\n" + "=" * 60)
            print("🎉 Cleanup process completed!")
            print("=" * 60)
            
            return deleted_count == len(exams)
            
        else:
            print(f"❌ Failed to fetch exams. Status: {response.status_code}")
            print(f"   Error: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        return False

def main():
    print("This tool will delete ALL exams from the database.")
    print("Make sure you have backups if needed!")
    print()
    
    start = input("Start cleanup process? (yes/no): ").strip().lower()
    
    if start == 'yes':
        clear_all_exams_safely()
    else:
        print("❌ Cleanup cancelled.")

if __name__ == "__main__":
    main()