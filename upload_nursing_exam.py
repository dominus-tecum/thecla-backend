import os
import re
import uuid
from docx import Document
import requests

def extract_questions_from_text(text, exam_uuid):
    questions = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    i = 0
    question_count = 0  # Counter for question numbers
    
    while i < len(lines):
        q_match = re.match(r'^\d+\.\s+(.*)', lines[i])
        if q_match:
            question_count += 1  # Increment question counter
            question_text = q_match.group(1)
            options = []
            i += 1
            
            # FIXED: Collect options with both . and ) formats
            while i < len(lines) and re.match(r'^[a-dA-D][\.\)]', lines[i]):
                # FIXED: Remove both . and ) from options
                option_text = re.sub(r'^[a-dA-D][\.\)]\s*', '', lines[i])
                options.append(option_text)
                i += 1
            
            correct_idx = -1
            rationale = None
            
            # FIXED: Find correct answer - handle both formats
            while i < len(lines) and (
                re.match(r'^(?:✅\s*)?(?:Correct\s*)?Answer:', lines[i], re.IGNORECASE)
            ):
                # FIXED: Handle both "Answer: B" and "Answer: B. Text" formats
                ans_match = re.match(
                    r'^(?:✅\s*)?(?:Correct\s*)?Answer:\s*([a-dA-D])(?:\.|\)|\s|$)', lines[i], re.IGNORECASE
                )
                if ans_match:
                    correct_letter = ans_match.group(1).lower()
                    correct_idx = ['a', 'b', 'c', 'd'].index(correct_letter)
                    # Move to next line after finding answer
                    i += 1
                    break
                i += 1
            
            # FIXED: BETTER RATIONALE EXTRACTION
            if i < len(lines) and 'rationale:' in lines[i].lower():
                # Extract everything after "Rationale:"
                rationale_line = lines[i]
                rationale = rationale_line.split('Rationale:', 1)[-1].split('rationale:', 1)[-1].strip()
                print(f"🔍 FOUND RATIONALE: {rationale[:50]}...")  # Debug print
                i += 1
            
            if correct_idx == -1:
                print(f"WARNING: No correct answer found for question: '{question_text}'")
            
            questions.append({
                'id': str(uuid.uuid4()),
                'exam_id': exam_uuid,
                'text': question_text,
                'options': options,
                'correct_idx': correct_idx,
                'rationale': rationale
            })
            
            # Debug: Show what we found WITH QUESTION NUMBER
            print(f"📝 Question #{question_count}: {question_text[:50]}...")
            print(f"   Options: {len(options)}")
            # FIXED: Show both index and letter for clarity
            correct_letter = chr(97 + correct_idx) if correct_idx != -1 else 'NOT FOUND'
            print(f"   Correct: {correct_idx} ({correct_letter.upper()})")
            print(f"   Rationale: {'YES' if rationale else 'NO'}")
            
        else:
            i += 1
    return questions

# NEW: PROFESSION SELECTION FOR ALL 8 DISCIPLINES
def get_profession_from_user():
    """Ask user which profession to upload exams for"""
    disciplines = {
        '1': ('gp', 'General Practitioner'),
        '2': ('nurse', 'Nurse'),
        '3': ('midwife', 'Midwife'),
        '4': ('lab_tech', 'Lab Technologist'),
        '5': ('physiotherapist', 'Physiotherapist'),
        '6': ('icu_nurse', 'ICU Nurse'),
        '7': ('emergency_nurse', 'Emergency Nurse'),
        '8': ('neonatal_nurse', 'Neonatal Nurse')
    }
    
    print("\n🎯 SELECT PROFESSION FOR EXAM UPLOAD:")
    print("=" * 50)
    print("   1. General Practitioner (gp)")
    print("   2. Nurse (nurse)")
    print("   3. Midwife (midwife)")
    print("   4. Lab Technologist (lab_tech)")
    print("   5. Physiotherapist (physiotherapist)")
    print("   6. ICU Nurse (icu_nurse)")
    print("   7. Emergency Nurse (emergency_nurse)")
    print("   8. Neonatal Nurse (neonatal_nurse)")
    print("=" * 50)
    
    while True:
        choice = input("\nEnter your choice (1-8): ").strip()
        if choice in disciplines:
            discipline_id, discipline_name = disciplines[choice]
            print(f"✅ Selected: {discipline_name} (discipline_id: {discipline_id})")
            return discipline_id, discipline_name
        else:
            print("❌ Invalid choice. Please enter a number between 1-8")

# NEW: DYNAMIC FOLDER PATHS FOR EACH PROFESSION
def get_folder_path(discipline_id):
    """Get the appropriate folder path for each discipline"""
    base_path = r'd:\Thecla\Training Examinations'
    
    folder_mapping = {
        'gp': r'GP\Exams\Rationale',
        'nurse': r'Nurses\Prometric Exam\Rationale',
        'midwife': r'Midwives\Exams',
        'lab_tech': r'Lab Technologists\Exams',
        'physiotherapist': r'Physiotherapists\Exams',
        'icu_nurse': r'Specialty Nurses\ICU\Exams',
        'emergency_nurse': r'Specialty Nurses\Emergency\Exams',
        'neonatal_nurse': r'Specialty Nurses\Neonatal\Exams'
    }
    
    folder = folder_mapping.get(discipline_id, 'Exams')
    full_path = os.path.join(base_path, folder)
    
    # Create folder if it doesn't exist
    if not os.path.exists(full_path):
        print(f"📁 Creating folder: {full_path}")
        os.makedirs(full_path, exist_ok=True)
    
    return full_path

# NEW: CHECK FOR EXISTING EXAM
def check_existing_exam(exam_title, discipline_id):
    """Check if an exam with similar name already exists"""
    try:
        # Search for exams by title and discipline
        search_url = f'{API_URL}search'
        params = {
            'title': exam_title,
            'discipline_id': discipline_id
        }
        response = requests.get(search_url, params=params)
        
        if response.status_code == 200:
            existing_exams = response.json()
            if existing_exams:
                return existing_exams[0]  # Return first matching exam
        return None
    except Exception as e:
        print(f"⚠️  Warning: Could not check for existing exams: {e}")
        return None

# NEW: DELETE EXISTING EXAM
def delete_existing_exam(exam_id):
    """Delete an existing exam"""
    try:
        delete_url = f'{API_URL}{exam_id}'
        response = requests.delete(delete_url)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error deleting existing exam: {e}")
        return False

# NEW: CONFIRM OVERWRITE
def confirm_overwrite(exam_title, existing_exam):
    """Ask user for confirmation to overwrite existing exam"""
    print(f"\n⚠️  DUPLICATE EXAM FOUND!")
    print(f"   Existing: {existing_exam.get('title', 'Unknown')} (ID: {existing_exam.get('id', 'Unknown')})")
    print(f"   New: {exam_title}")
    print(f"   Questions in existing exam: {len(existing_exam.get('questions', []))}")
    
    while True:
        choice = input("\nDo you want to replace the existing exam? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
        else:
            print("❌ Please enter 'y' for yes or 'n' for no")

# NEW: UPLOAD SINGLE EXAM FILE
def upload_single_exam():
    """Upload or update a specific exam file"""
    print("\n🎯 SINGLE EXAM UPLOAD")
    print("=" * 40)
    
    # Get profession
    discipline_id, discipline_name = get_profession_from_user()
    folder_path = get_folder_path(discipline_id)
    
    # List available files
    docx_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.docx') and not f.startswith('~$')]
    
    if not docx_files:
        print(f"❌ No .docx files found in: {folder_path}")
        return
    
    print(f"\n📄 Available exams in {discipline_name} folder:")
    for i, filename in enumerate(docx_files, 1):
        print(f"   {i}. {filename}")
    
    # Let user select file
    while True:
        try:
            choice = input(f"\nSelect exam file (1-{len(docx_files)}): ").strip()
            file_index = int(choice) - 1
            if 0 <= file_index < len(docx_files):
                filename = docx_files[file_index]
                break
            else:
                print(f"❌ Please enter a number between 1-{len(docx_files)}")
        except ValueError:
            print("❌ Please enter a valid number")
    
    # Process the selected file
    process_exam_file(filename, folder_path, discipline_id, discipline_name)

# NEW: PROCESS SINGLE EXAM FILE
def process_exam_file(filename, folder_path, discipline_id, discipline_name):
    """Process and upload a single exam file"""
    doc_path = os.path.join(folder_path, filename)
    try:
        exam_uuid = str(uuid.uuid4())
        document = Document(doc_path)
        full_text = '\n'.join([para.text for para in document.paragraphs])
        
        # DEBUG: Show raw text structure
        print(f"\n🔍 PROCESSING: {filename}")
        print("=" * 50)
        
        questions = extract_questions_from_text(full_text, exam_uuid)
        exam_title = filename.replace('.docx', '')
        
        # CHECK FOR EXISTING EXAM
        existing_exam = check_existing_exam(exam_title, discipline_id)
        if existing_exam:
            if confirm_overwrite(exam_title, existing_exam):
                print("🗑️  Deleting existing exam...")
                if delete_existing_exam(existing_exam['id']):
                    print("✅ Existing exam deleted successfully")
                else:
                    print("❌ Failed to delete existing exam. Skipping upload.")
                    return
            else:
                print("⏭️  Skipping upload - keeping existing exam")
                return
        
        # Prepare payload
        payload = {
            "id": exam_uuid,
            "title": exam_title,
            "discipline_id": discipline_id,
            "time_limit": 50,
            "source": "plural",
            "is_released": False,
            "questions": questions
        }
        
        print(f"\n📤 Uploading {discipline_name} exam: {exam_title}")
        print(f"🎯 Discipline: {discipline_name} ({discipline_id})")
        print(f"❓ Questions: {len(questions)}")
        
        questions_with_rationale = [q for q in questions if q.get('rationale')]
        print(f"📚 Questions with rationale: {len(questions_with_rationale)}/{len(questions)}")
        
        # Upload exam
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ SUCCESS: {exam_title} - Status: {response.status_code}")
            print(f"💡 Remember to release this exam via /admin/exams/{exam_uuid}/release")
        else:
            print(f"❌ FAILED: {exam_title} - Status: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"💥 Error processing {doc_path}: {e}")

# NEW: BATCH UPLOAD ALL EXAMS
def upload_all_exams():
    """Upload all exams in a folder (original functionality)"""
    discipline_id, discipline_name = get_profession_from_user()
    folder_path = get_folder_path(discipline_id)

    print(f"\n📁 Scanning folder: {folder_path}")
    print(f"🎯 Uploading exams for: {discipline_name}")

    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"❌ Folder not found: {folder_path}")
        print("💡 Please create the folder and add exam documents, or check the path configuration.")
        return

    # Get all .docx files in the folder
    docx_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.docx') and not f.startswith('~$')]

    if not docx_files:
        print(f"❌ No .docx files found in: {folder_path}")
        print("💡 Please add exam documents (.docx files) to the folder and try again.")
        return

    print(f"📄 Found {len(docx_files)} exam file(s) to process")

    for filename in docx_files:
        process_exam_file(filename, folder_path, discipline_id, discipline_name)

    print(f"\n🎉 Upload session completed for {discipline_name}!")
    print(f"📁 Files were processed from: {folder_path}")

# MAIN UPLOAD SCRIPT
API_URL = 'https://thecla-backend.onrender.com/exams/'  # Plural endpoint

def main():
    """Main menu for exam upload options"""
    print("🎯 EXAM UPLOAD MANAGER")
    print("=" * 40)
    print("1. Upload/Update a Specific Exam")
    print("2. Upload All Exams in Folder (Batch)")
    print("3. Exit")
    print("=" * 40)
    
    while True:
        choice = input("\nSelect option (1-3): ").strip()
        if choice == '1':
            upload_single_exam()
            break
        elif choice == '2':
            upload_all_exams()
            break
        elif choice == '3':
            print("👋 Exiting...")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3")

if __name__ == "__main__":
    main()