import os
import re
import uuid
from docx import Document
import requests


def extract_questions_from_text(text, exam_uuid):
    """
    Robust exam parser using state machine approach with Component 1's rationale extraction.
    """
    
    class QuestionParser:
        def __init__(self, all_lines):
            self.state = 'FINDING_QUESTION'
            self.current_q = None
            self.questions = []
            self.question_count = 0
            self.skipped_questions = []  # Track skipped questions
            self.missing_rationale_questions = []  # NEW: Track questions missing rationale
            self.all_lines = all_lines  # Store all lines for lookahead
            
            # Patterns (compiled once for efficiency)
            self.q_start_pattern = re.compile(r'^\s*\d+\s*[\.\)]')
            self.option_pattern = re.compile(r'^\s*\(?\s*([a-dA-D])\s*\)?\s*[\.\)]')
            self.answer_pattern = re.compile(
                r'(?:✅\s*)?(?:Correct\s*)?(?:Answer|Ans\.?)\s*[:\.]?\s*\(?\s*([a-dA-D])\s*\)?\s*[\.\)]?',
                re.IGNORECASE
            )
            
        def process_line(self, line_num, line, current_idx):
            raw_line = line  # Keep original for debugging
            line = line.strip()
            
            # Skip empty lines in most states
            if not line and self.state not in ['COLLECTING_OPTION_CONTINUATION', 'COLLECTING_QUESTION']:
                return
                
            if self.state == 'FINDING_QUESTION':
                if self.q_start_pattern.match(line):
                    self.question_count += 1
                    # Extract question number - more flexible regex
                    match = re.match(r'^\s*(\d+)\s*[\.\)]\s*(.*)', line)
                    if match:
                        q_num = match.group(1)
                        remaining_text = match.group(2)
                        
                        self.current_q = {
                            'id': str(uuid.uuid4()),
                            'exam_id': exam_uuid,
                            'number': q_num,
                            'text': remaining_text.strip(),
                            'options': [],
                            'correct_idx': -1,
                            'rationale': None
                        }
                        
                        if self.current_q['text']:
                            self.state = 'COLLECTING_QUESTION'
                        else:
                            self.state = 'WAITING_FOR_QUESTION_TEXT'
                            
            elif self.state == 'WAITING_FOR_QUESTION_TEXT':
                # Sometimes question number is on its own line
                if line:
                    self.current_q['text'] = line
                    self.state = 'COLLECTING_QUESTION'
                    
            elif self.state == 'COLLECTING_QUESTION':
                # Check for transition conditions
                if self.option_pattern.match(line):
                    # Options starting
                    self.state = 'COLLECTING_OPTIONS'
                    self.process_line(line_num, raw_line, current_idx)  # Reprocess as option
                elif self.answer_pattern.search(line):
                    # Answer found (question ended abruptly)
                    self.state = 'PROCESSING_ANSWER'
                    self.process_line(line_num, line, current_idx)
                elif self.q_start_pattern.match(line):
                    # Next question found (save current one first)
                    self.save_question()
                    self.state = 'FINDING_QUESTION'
                    self.process_line(line_num, line, current_idx)
                else:
                    # Add to question text
                    if self.current_q['text']:
                        self.current_q['text'] += ' ' + line
                    else:
                        self.current_q['text'] = line
                        
            elif self.state == 'COLLECTING_OPTIONS':
                if self.option_pattern.match(line):
                    # New option starting
                    option_text = re.sub(r'^\s*\(?\s*[a-dA-D]\s*\)?\s*[\.\)]\s*', '', line, flags=re.IGNORECASE)
                    self.current_q['options'].append(option_text.strip())
                    
                    # Check if we should continue collecting this option
                    self.state = 'COLLECTING_OPTION_CONTINUATION'
                    
                elif self.answer_pattern.search(line):
                    self.state = 'PROCESSING_ANSWER'
                    self.process_line(line_num, line, current_idx)
                elif 'rationale:' in line.lower():
                    # ========== COMPONENT 1'S RATIONALE LOGIC ==========
                    self.current_q['rationale'] = line.split('Rationale:', 1)[-1].split('rationale:', 1)[-1].strip()
                    print(f"🔍 FOUND RATIONALE: {self.current_q['rationale'][:50]}...")
                    self.save_question()
                    self.state = 'FINDING_QUESTION'
                    # ===================================================
                elif self.q_start_pattern.match(line):
                    self.save_question()
                    self.state = 'FINDING_QUESTION'
                    self.process_line(line_num, line, current_idx)
                    
            elif self.state == 'COLLECTING_OPTION_CONTINUATION':
                # Check if this line is:
                # 1. Another option
                # 2. Answer
                # 3. Rationale
                # 4. Next question
                # 5. Continuation of current option
                
                if self.option_pattern.match(line):
                    # New option
                    self.state = 'COLLECTING_OPTIONS'
                    self.process_line(line_num, line, current_idx)
                elif self.answer_pattern.search(line):
                    self.state = 'PROCESSING_ANSWER'
                    self.process_line(line_num, line, current_idx)
                elif 'rationale:' in line.lower():
                    # ========== COMPONENT 1'S RATIONALE LOGIC ==========
                    self.current_q['rationale'] = line.split('Rationale:', 1)[-1].split('rationale:', 1)[-1].strip()
                    print(f"🔍 FOUND RATIONALE: {self.current_q['rationale'][:50]}...")
                    self.save_question()
                    self.state = 'FINDING_QUESTION'
                    # ===================================================
                elif self.q_start_pattern.match(line):
                    self.save_question()
                    self.state = 'FINDING_QUESTION'
                    self.process_line(line_num, line, current_idx)
                elif line:  # Continuation of current option
                    if self.current_q['options']:
                        self.current_q['options'][-1] += ' ' + line
                        self.state = 'COLLECTING_OPTION_CONTINUATION'
                    else:
                        # Shouldn't happen, but fallback
                        self.state = 'COLLECTING_OPTIONS'
                        
            elif self.state == 'PROCESSING_ANSWER':
                # Extract answer
                ans_match = self.answer_pattern.search(line)
                if ans_match:
                    letter = ans_match.group(1).lower()
                    try:
                        self.current_q['correct_idx'] = ['a', 'b', 'c', 'd'].index(letter)
                    except ValueError:
                        print(f"⚠️  Invalid answer letter '{letter}' in Q{self.current_q['number']}")
                
                # ========== COMPONENT 1'S RATIONALE LOGIC ==========
                # Check for rationale immediately after answer
                if current_idx + 1 < len(self.all_lines) and 'rationale:' in self.all_lines[current_idx + 1].lower():
                    rationale_line = self.all_lines[current_idx + 1]
                    self.current_q['rationale'] = rationale_line.split('Rationale:', 1)[-1].split('rationale:', 1)[-1].strip()
                    print(f"🔍 FOUND RATIONALE (next line): {self.current_q['rationale'][:50]}...")
                    self.save_question()
                    self.state = 'FINDING_QUESTION'
                else:
                    # No rationale found, save question and continue
                    self.save_question()
                    self.state = 'FINDING_QUESTION'
                # ===================================================
                
        def save_question(self):
            """Save current question if valid"""
            if not self.current_q:
                return
                
            # Validation checks
            is_valid = True
            issues = []
            q_number = self.current_q['number']
            
            if not self.current_q['text'] or len(self.current_q['text'].strip()) < 5:
                issues.append("Question text too short")
                is_valid = False
                
            if len(self.current_q['options']) < 2:
                issues.append(f"Only {len(self.current_q['options'])} options (need at least 2)")
                is_valid = False
            elif len(self.current_q['options']) > 6:
                issues.append(f"Too many options: {len(self.current_q['options'])} (max 6)")
                # Still accept, but note
                print(f"⚠️  Q{self.current_q['number']}: Has {len(self.current_q['options'])} options")
                
            if self.current_q['correct_idx'] == -1:
                issues.append("No correct answer found")
                is_valid = False
                
            # Check for duplicate option text
            if is_valid and len(set(self.current_q['options'])) != len(self.current_q['options']):
                issues.append("Duplicate options found")
                is_valid = False
                
            if is_valid:
                # Clean up the question
                self.current_q['text'] = self.current_q['text'].strip()
                self.current_q['options'] = [opt.strip() for opt in self.current_q['options'] if opt.strip()]
                
                # Remove internal fields before adding
                q_data = {
                    'id': self.current_q['id'],
                    'exam_id': self.current_q['exam_id'],
                    'text': self.current_q['text'],
                    'options': self.current_q['options'],
                    'correct_idx': self.current_q['correct_idx'],
                    'rationale': self.current_q['rationale'].strip() if self.current_q['rationale'] else None
                }
                
                self.questions.append(q_data)
                
                # NEW: Track questions missing rationale
                if not q_data['rationale']:
                    missing_info = {
                        'number': q_number,
                        'text_preview': q_data['text'][:100] if q_data['text'] else '[No text]',
                        'options_count': len(q_data['options'])
                    }
                    self.missing_rationale_questions.append(missing_info)
                    print(f"✅ Q{self.current_q['number']}: Saved ({len(self.current_q['options'])} options) - ⚠️ NO RATIONALE")
                else:
                    print(f"✅ Q{self.current_q['number']}: Saved ({len(self.current_q['options'])} options) - ✅ WITH RATIONALE")
            else:
                # Track skipped questions with details
                skip_info = {
                    'number': q_number,
                    'reasons': issues,
                    'text_preview': self.current_q['text'][:100] if self.current_q['text'] else '[No text]',
                    'options_count': len(self.current_q['options']),
                    'has_answer': self.current_q['correct_idx'] != -1
                }
                self.skipped_questions.append(skip_info)
                print(f"❌ Q{q_number}: SKIPPED - {', '.join(issues)}")
                print(f"   📝 Preview: {skip_info['text_preview']}...")
                
            # Reset current question
            self.current_q = None
                
        def get_questions(self):
            # Save any pending question
            if self.current_q:
                self.save_question()
            return self.questions
        
        def get_skipped_questions(self):
            """Return list of skipped questions with details"""
            return self.skipped_questions
        
        def get_missing_rationale_questions(self):
            """Return list of questions missing rationale"""
            return self.missing_rationale_questions
    
    # --- Main processing ---
    print(f"\n{'='*60}")
    print("🧠 STATE MACHINE PARSER WITH COMPONENT 1 RATIONALE LOGIC")
    print(f"{'='*60}")
    
    # First, clean up the text
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    lines = text.split('\n')
    parser = QuestionParser(lines)  # Pass lines to the parser
    
    # Process all lines
    for idx, line in enumerate(lines):
        parser.process_line(idx + 1, line, idx)  # Pass current index
    
    # Get all parsed questions
    questions = parser.get_questions()
    skipped_questions = parser.get_skipped_questions()
    missing_rationale_questions = parser.get_missing_rationale_questions()
    
    # Summary statistics
    print(f"\n{'='*60}")
    print("📊 EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total lines processed: {len(lines)}")
    print(f"Questions found: {parser.question_count}")
    print(f"Valid questions saved: {len(questions)}")
    print(f"Skipped questions (invalid format): {len(skipped_questions)}")
    print(f"Questions missing rationale: {len(missing_rationale_questions)}")
    
    # NEW: Detailed skipped questions report (invalid format)
    if skipped_questions:
        print(f"\n{'='*60}")
        print("❌ SKIPPED QUESTIONS (INVALID FORMAT)")
        print(f"{'='*60}")
        for idx, skip in enumerate(skipped_questions, 1):
            print(f"\n{idx}. Question #{skip['number']} - SKIPPED")
            print(f"   Reasons:")
            for reason in skip['reasons']:
                print(f"      • {reason}")
            print(f"   Text preview: {skip['text_preview']}")
            print(f"   Options found: {skip['options_count']}")
            print(f"   Has answer key: {'Yes' if skip['has_answer'] else 'No'}")
    else:
        print(f"\n✅ No questions were skipped due to invalid format!")
    
    # NEW: Detailed missing rationale report
    if missing_rationale_questions:
        print(f"\n{'='*60}")
        print("⚠️  QUESTIONS MISSING RATIONALE")
        print(f"{'='*60}")
        print(f"Found {len(missing_rationale_questions)} question(s) without rationale text:")
        for idx, missing in enumerate(missing_rationale_questions, 1):
            print(f"\n{idx}. Question #{missing['number']}")
            print(f"   Text preview: {missing['text_preview']}...")
            print(f"   Options: {missing['options_count']}")
            print(f"   💡 Suggestion: Add 'Rationale:' text after the correct answer")
    else:
        print(f"\n✅ All {len(questions)} questions have rationale text!")
    
    if questions:
        questions_with_rationale = sum(1 for q in questions if q.get('rationale'))
        print(f"\n📚 Questions with rationale: {questions_with_rationale}/{len(questions)}")
        
        # Show sample of first question
        if len(questions) > 0:
            print(f"\n📋 SAMPLE QUESTION (first of {len(questions)}):")
            q = questions[0]
            print(f"Text: {q['text'][:80]}...")
            print(f"Options: {len(q['options'])}")
            for i, opt in enumerate(q['options'][:4]):
                print(f"  {chr(97+i)}) {opt[:50]}{'...' if len(opt) > 50 else ''}")
            correct_letter = chr(97 + q['correct_idx']) if q['correct_idx'] >= 0 else '?'
            print(f"Correct: {correct_letter.upper()}")
            if q.get('rationale'):
                print(f"Rationale: {q['rationale'][:60]}...")
            else:
                print(f"Rationale: ❌ MISSING")
    
    print(f"{'='*60}")
    
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
        '8': ('neonatal_nurse', 'Neonatal Nurse'),
        '9': ('pharmacist', 'Pharmacist')

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
    print("   9. Pharmacist (pharmacist)")
    print("=" * 50)
    
    while True:
        choice = input("\nEnter your choice (1-9): ").strip()
        if choice in disciplines:
            discipline_id, discipline_name = disciplines[choice]
            print(f"✅ Selected: {discipline_name} (discipline_id: {discipline_id})")
            return discipline_id, discipline_name
        else:
            print("❌ Invalid choice. Please enter a number between 1-9")

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
        'neonatal_nurse': r'Specialty Nurses\Neonatal\Exams',
        'pharmacist': r'Pharmacist\Exams'
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
        search_url = f'{API_URL.rstrip("/")}/search'  # Remove trailing slash and add /search
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
        
        # ✅ FIXED: CHECK FOR EXISTING EXAM (with better debugging)
        print(f"🔍 Checking for existing exam: '{exam_title}' in {discipline_id}")
        existing_exam = check_existing_exam(exam_title, discipline_id)
        
        if existing_exam:
            print(f"⚠️  FOUND EXISTING EXAM: {existing_exam.get('title')} (ID: {existing_exam.get('id')})")
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
        else:
            print("✅ No existing exam found - proceeding with upload")
        
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
        
        if len(questions_with_rationale) < len(questions):
            missing_count = len(questions) - len(questions_with_rationale)
            print(f"⚠️  WARNING: {missing_count} question(s) are missing rationale text!")
        
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
API_URL = 'https://thecla-backend.onrender.com/exams/'
#API_URL = 'https://76f3bda79ccd.ngrok-free.app/exams/'

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