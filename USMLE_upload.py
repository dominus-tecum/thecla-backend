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
            
            if not self.current_q['text'] or len(self.current_q['text'].strip()) < 5:
                issues.append("Question text too short")
                is_valid = False
                
            if len(self.current_q['options']) < 2:
                issues.append(f"Only {len(self.current_q['options'])} options")
                is_valid = False
            elif len(self.current_q['options']) > 6:
                issues.append(f"Too many options: {len(self.current_q['options'])}")
                # Still accept, but note
                print(f"⚠️  Q{self.current_q['number']}: Has {len(self.current_q['options'])} options")
                
            if self.current_q['correct_idx'] == -1:
                issues.append("No correct answer")
                is_valid = False
                
            if is_valid:
                # Clean up the question
                self.current_q['text'] = self.current_q['text'].strip()
                self.current_q['options'] = [opt.strip() for opt in self.current_q['options'] if opt.strip()]
                
                # Remove internal fields before adding
                q_data = {
                    'id': self.current_q['id'],
                    'exam_id': exam_uuid,
                    'text': self.current_q['text'],
                    'options': self.current_q['options'],
                    'correct_idx': self.current_q['correct_idx'],
                    'rationale': self.current_q['rationale'].strip() if self.current_q['rationale'] else None
                }
                
                self.questions.append(q_data)
                print(f"✅ Q{self.current_q['number']}: Saved ({len(self.current_q['options'])} options)")
            else:
                print(f"❌ Q{self.current_q['number']}: Skipped - {', '.join(issues)}")
                
            # Reset current question
            self.current_q = None
                
        def get_questions(self):
            # Save any pending question
            if self.current_q:
                self.save_question()
            return self.questions
    
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
    
    # Summary statistics
    print(f"\n{'='*60}")
    print("📊 EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total lines processed: {len(lines)}")
    print(f"Questions found: {parser.question_count}")
    print(f"Valid questions saved: {len(questions)}")
    
    if questions:
        questions_with_rationale = sum(1 for q in questions if q.get('rationale'))
        print(f"Questions with rationale: {questions_with_rationale}/{len(questions)}")
        
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
    
    print(f"{'='*60}")
    
    return questions




# CHANGED: ONLY USMLE OPTION
def get_profession_from_user():
    """USMLE only"""
    disciplines = {
        '1': ('usmle', 'USMLE (Medical Licensing)'),
    }
    
    print("\n🎯 USMLE EXAM UPLOAD")
    print("=" * 50)
    print("   1. USMLE (Medical Licensing)")
    print("=" * 50)
    
    # Auto-select option 1 (USMLE)
    choice = '1'
    discipline_id, discipline_name = disciplines[choice]
    print(f"✅ Selected: {discipline_name} (discipline_id: {discipline_id})")
    return discipline_id, discipline_name

# CHANGED: ONLY USMLE FOLDER PATH
def get_folder_path(discipline_id):
    """Get USMLE folder path"""
    base_path = r'd:\Thecla\Training Examinations'
    
    folder_mapping = {
        'usmle': r'USMLE\Exams',
    }
    
    folder = folder_mapping.get(discipline_id, 'Exams')
    full_path = os.path.join(base_path, folder)
    
    # Create folder if it doesn't exist
    if not os.path.exists(full_path):
        print(f"📁 Creating folder: {full_path}")
        os.makedirs(full_path, exist_ok=True)
    
    return full_path

# SAME: CHECK FOR EXISTING EXAM
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

# SAME: DELETE EXISTING EXAM
def delete_existing_exam(exam_id):
    """Delete an existing exam"""
    try:
        delete_url = f'{API_URL}{exam_id}'
        response = requests.delete(delete_url)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error deleting existing exam: {e}")
        return False

# SAME: CONFIRM OVERWRITE
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

# CHANGED: UPLOAD TO USMLE ENDPOINT
def upload_single_exam():
    """Upload or update a USMLE exam file"""
    print("\n🎯 USMLE EXAM UPLOAD")
    print("=" * 40)
    
    # Get USMLE profession
    discipline_id, discipline_name = get_profession_from_user()
    folder_path = get_folder_path(discipline_id)
    
    # List available files
    docx_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.docx') and not f.startswith('~$')]
    
    if not docx_files:
        print(f"❌ No .docx files found in: {folder_path}")
        return
    
    print(f"\n📄 Available USMLE exams:")
    for i, filename in enumerate(docx_files, 1):
        print(f"   {i}. {filename}")
    
    # Let user select file
    while True:
        try:
            choice = input(f"\nSelect USMLE exam file (1-{len(docx_files)}): ").strip()
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

# CHANGED: UPLOAD TO USMLE ENDPOINT
def process_exam_file(filename, folder_path, discipline_id, discipline_name):
    """Process and upload a USMLE exam file"""
    doc_path = os.path.join(folder_path, filename)
    try:
        exam_uuid = str(uuid.uuid4())
        document = Document(doc_path)
        full_text = '\n'.join([para.text for para in document.paragraphs])
        
        # DEBUG: Show raw text structure
        print(f"\n🔍 PROCESSING USMLE EXAM: {filename}")
        print("=" * 50)
        
        questions = extract_questions_from_text(full_text, exam_uuid)
        exam_title = filename.replace('.docx', '')
        
        # ✅ CHECK FOR EXISTING EXAM
        print(f"🔍 Checking for existing USMLE exam: '{exam_title}'")
        existing_exam = check_existing_exam(exam_title, discipline_id)
        
        if existing_exam:
            print(f"⚠️  FOUND EXISTING USMLE EXAM: {existing_exam.get('title')} (ID: {existing_exam.get('id')})")
            if confirm_overwrite(exam_title, existing_exam):
                print("🗑️  Deleting existing USMLE exam...")
                if delete_existing_exam(existing_exam['id']):
                    print("✅ Existing USMLE exam deleted successfully")
                else:
                    print("❌ Failed to delete existing USMLE exam. Skipping upload.")
                    return
            else:
                print("⏭️  Skipping upload - keeping existing USMLE exam")
                return
        else:
            print("✅ No existing USMLE exam found - proceeding with upload")
        
        # SAME PAYLOAD STRUCTURE, but goes to USMLE endpoint
        payload = {
            "id": exam_uuid,
            "title": exam_title,
            "discipline_id": discipline_id,
            "time_limit": 50,
            "source": "usmle",
            "is_released": False,
            "questions": questions
        }
        
        print(f"\n📤 Uploading USMLE exam: {exam_title}")
        print(f"🎯 Discipline: {discipline_name} ({discipline_id})")
        print(f"❓ Questions: {len(questions)}")
        
        questions_with_rationale = [q for q in questions if q.get('rationale')]
        print(f"📚 Questions with rationale: {len(questions_with_rationale)}/{len(questions)}")
        
        # CHANGED: Upload to USMLE endpoint
        usmle_endpoint = f'{API_URL.rstrip("/")}/usmle'
        response = requests.post(usmle_endpoint, json=payload)
        
        if response.status_code == 200:
            print(f"✅ SUCCESS: {exam_title} - Status: {response.status_code}")
            print(f"💡 Remember to release this exam via /admin/exams/{exam_uuid}/release")
        else:
            print(f"❌ FAILED: {exam_title} - Status: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"💥 Error processing USMLE exam {doc_path}: {e}")



# SAME
def upload_all_exams():
    """Upload all USMLE exams in folder"""
    discipline_id, discipline_name = get_profession_from_user()
    folder_path = get_folder_path(discipline_id)

    print(f"\n📁 Scanning USMLE folder: {folder_path}")
    print(f"🎯 Uploading USMLE exams")

    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"❌ USMLE folder not found: {folder_path}")
        print("💡 Please create the folder and add USMLE exam documents.")
        return

    # Get all .docx files in the folder
    docx_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.docx') and not f.startswith('~$')]

    if not docx_files:
        print(f"❌ No USMLE .docx files found in: {folder_path}")
        print("💡 Please add USMLE exam documents (.docx files) to the folder.")
        return

    print(f"📄 Found {len(docx_files)} USMLE exam file(s) to process")

    for filename in docx_files:
        process_exam_file(filename, folder_path, discipline_id, discipline_name)

    print(f"\n🎉 USMLE upload session completed!")
    print(f"📁 Files were processed from: {folder_path}")

# CHANGED: USMLE-SPECIFIC MENU
def main():
    """Main menu for USMLE exam upload"""
    print("🎯 USMLE EXAM UPLOAD MANAGER")
    print("=" * 40)
    print("1. Upload/Update a Specific USMLE Exam")
    print("2. Upload All USMLE Exams in Folder (Batch)")
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
            print("👋 Exiting USMLE upload...")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3")

# SAME API URL
API_URL = 'https://thecla-backend.onrender.com/exams/'

if __name__ == "__main__":
    main()