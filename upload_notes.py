import os
import re
import uuid
from docx import Document
import requests
import PyPDF2  # Add this for PDF support

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF files"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        print(f"❌ Error reading PDF {pdf_path}: {e}")
        return ""

def extract_reading_content_from_text(text, exam_uuid):
    sections = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    current_section = None
    
    for i, line in enumerate(lines):
        # Skip empty lines
        if not line:
            continue
            
        # IMPROVED: Focus on numbered subtopics for TOC items
        is_header = (
            re.match(r'^\d+\.\s+[A-Z]', line) or  # "1. Isotretinoin" - MAIN FIX
            re.match(r'^\d+\.\s+"', line) or       # "1. "Which client..." 
            # Keep some original patterns but make them stricter
            (re.match(r'^\d+\.\s+', line) and len(line) < 100) or
            re.match(r'^[IVX]+\.\s+[A-Z]', line)   # "I. Introduction"
        )
        
        if is_header:
            # Save previous section if exists - ORIGINAL LOGIC
            if current_section and (current_section['text'] or current_section['options']):
                sections.append(current_section)
            
            # Start new section - ORIGINAL LOGIC
            current_section = {
                'id': str(uuid.uuid4()),
                'exam_id': exam_uuid,
                'text': line,  # This is the section title/header
                'options': [],  # This will store the content paragraphs
                'correct_idx': -1
            }
        
        # If we're in a section and this line is content - ORIGINAL LOGIC
        elif current_section is not None:
            # Add the line as content (paragraph)
            current_section['options'].append(line)
        
        # If no section started yet, create one with the first line as title - ORIGINAL LOGIC
        elif current_section is None:
            current_section = {
                'id': str(uuid.uuid4()),
                'exam_id': exam_uuid,
                'text': "Content Overview",  # Default title
                'options': [line],  # First line as content
                'correct_idx': -1
            }
    
    # Don't forget the last section - ORIGINAL LOGIC
    if current_section and (current_section['text'] or current_section['options']):
        sections.append(current_section)
    
    # If no sections found, treat everything as one section - ORIGINAL LOGIC
    if not sections and lines:
        sections.append({
            'id': str(uuid.uuid4()),
            'exam_id': exam_uuid,
            'text': "Reading Material",  # Default title
            'options': lines,  # All lines as content
            'correct_idx': -1
        })
    
    print(f"📖 Extracted {len(sections)} sections from document")
    for i, section in enumerate(sections):
        print(f"  Section {i+1}: '{section['text'][:50]}...' - {len(section['options'])} content lines")
    
    return sections


# NEW: PROFESSION SELECTION FOR ALL 8 DISCIPLINES
def get_profession_from_user():
    """Ask user which profession to upload reading materials for"""
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
    
    print("\n🎯 SELECT PROFESSION FOR READING MATERIALS:")
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

# NEW: DYNAMIC FOLDER PATHS FOR EACH PROFESSION'S READING MATERIALS
def get_reading_materials_folder_path(discipline_id):
    """Get the appropriate reading materials folder path for each discipline"""
    base_path = r'd:\Thecla\Training Examinations'
    
    folder_mapping = {
        'gp': r'GP\Study Notes',
        'nurse': r'Nurses\Study Notes',
        'midwife': r'Midwives\Reading Materials',
        'lab_tech': r'Lab Technologists\Reading Materials',
        'physiotherapist': r'Physiotherapists\Reading Materials',
        'icu_nurse': r'Specialty Nurses\ICU\Reading Materials',
        'emergency_nurse': r'Specialty Nurses\Emergency\Reading Materials',
        'neonatal_nurse': r'Neonate\Notes'
    }
    
    folder = folder_mapping.get(discipline_id, 'Reading Materials')
    full_path = os.path.join(base_path, folder)
    
    # Create folder if it doesn't exist
    if not os.path.exists(full_path):
        print(f"📁 Creating folder: {full_path}")
        os.makedirs(full_path, exist_ok=True)
    
    return full_path

# NEW: CHECK IF FILE ALREADY EXISTS ON SERVER
def check_file_exists_on_server(filename, discipline_id):
    """Check if a file with the same title already exists on the server"""
    try:
        exam_title = os.path.splitext(filename)[0]
        
        # First, try to get all exams for this discipline
        response = requests.get(f"{BASE_URL}/exams")
        if response.status_code == 200:
            all_exams = response.json()
            # Look for exams with same title and discipline
            for exam in all_exams:
                if exam.get('title') == exam_title and exam.get('discipline_id') == discipline_id:
                    return True, exam.get('id')  # Return True and the existing exam ID
        return False, None
    except Exception as e:
        print(f"⚠️  Could not check server for existing files: {e}")
        return False, None

# NEW: FILE SELECTION MENU
def select_files_to_upload(all_files):
    """Let user choose which files to upload"""
    print(f"\n📄 Found {len(all_files)} document file(s):")
    for i, filename in enumerate(all_files, 1):
        print(f"   {i}. {filename}")
    
    while True:
        print("\n📋 UPLOAD OPTIONS:")
        print("   1. Upload ALL files")
        print("   2. Select specific files")
        
        choice = input("\nEnter your choice (1 or 2): ").strip()
        
        if choice == '1':
            return all_files  # Return all files
        elif choice == '2':
            return select_specific_files(all_files)
        else:
            print("❌ Invalid choice. Please enter 1 or 2")

# NEW: SPECIFIC FILE SELECTION
def select_specific_files(all_files):
    """Let user select specific files from the list"""
    selected_files = []
    
    print("\n🔍 SELECT FILES (enter numbers separated by spaces):")
    for i, filename in enumerate(all_files, 1):
        print(f"   {i}. {filename}")
    
    while True:
        try:
            selections = input("\nEnter file numbers (e.g., 1 3 5): ").strip().split()
            if not selections:
                print("❌ Please select at least one file")
                continue
            
            selected_indices = []
            for sel in selections:
                idx = int(sel) - 1
                if 0 <= idx < len(all_files):
                    selected_indices.append(idx)
                else:
                    print(f"❌ Invalid number: {sel}. Please choose between 1-{len(all_files)}")
            
            if selected_indices:
                selected_files = [all_files[i] for i in selected_indices]
                print(f"\n✅ Selected {len(selected_files)} file(s):")
                for filename in selected_files:
                    print(f"   📄 {filename}")
                return selected_files
            else:
                print("❌ No valid files selected")
                
        except ValueError:
            print("❌ Please enter numbers only")

# NEW: CONFIRM FILE REPLACEMENT
def confirm_file_replacement(filename):
    """Ask user for confirmation before replacing existing file"""
    while True:
        choice = input(f"🔄 File '{filename}' already exists. Replace it? (y/n): ").strip().lower()
        if choice in ['y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
        else:
            print("❌ Please enter 'y' for yes or 'n' for no")

# MAIN UPLOAD SCRIPT FOR READING MATERIALS
BASE_URL = "https://thecla-backend.onrender.com"
#BASE_URL = "https://7215b3fb2cc3.ngrok-free.app"
API_URL = f'{BASE_URL}/exam/'  # Singular endpoint

# NEW: Ask user which profession to upload reading materials for
discipline_id, discipline_name = get_profession_from_user()
folder_path = get_reading_materials_folder_path(discipline_id)

print(f"\n📁 Scanning folder: {folder_path}")
print(f"🎯 Uploading reading materials for: {discipline_name}")

# Check if folder exists
if not os.path.exists(folder_path):
    print(f"❌ Folder not found: {folder_path}")
    print("💡 Please create the folder and add reading material documents, or check the path configuration.")
    exit()

# Get all .docx AND .pdf files in the folder
docx_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.docx') and not f.startswith('~$')]
pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]

all_files = docx_files + pdf_files

if not all_files:
    print(f"❌ No document files found in: {folder_path}")
    print("💡 Please add reading material documents (.docx or .pdf files) to the folder and try again.")
    exit()

# NEW: FILE SELECTION PROCESS
files_to_upload = select_files_to_upload(all_files)

print(f"\n🚀 Ready to upload {len(files_to_upload)} file(s)")

uploaded_count = 0
skipped_count = 0

for filename in files_to_upload:
    file_path = os.path.join(folder_path, filename)
    try:
        # NEW: CHECK FOR EXISTING FILE ON SERVER
        file_exists, existing_exam_id = check_file_exists_on_server(filename, discipline_id)
        
        if file_exists:
            if not confirm_file_replacement(filename):
                print(f"⏭️  Skipping '{filename}' - user chose not to replace")
                skipped_count += 1
                continue
            # If replacing, we'll use the existing exam ID instead of generating a new one
            exam_uuid = existing_exam_id or str(uuid.uuid4())
            replacement_note = " (REPLACING EXISTING)"
        else:
            exam_uuid = str(uuid.uuid4())
            replacement_note = " (NEW)"
        
        # Handle different file types
        if filename.lower().endswith('.docx'):
            # Process Word document
            document = Document(file_path)
            full_text = '\n'.join([para.text for para in document.paragraphs])
            file_type = "Word Document"
            
        elif filename.lower().endswith('.pdf'):
            # Process PDF document
            full_text = extract_text_from_pdf(file_path)
            file_type = "PDF Document"
            
        else:
            print(f"❌ Unsupported file type: {filename}")
            skipped_count += 1
            continue
        
        if not full_text.strip():
            print(f"⚠️  No text extracted from: {filename}")
            skipped_count += 1
            continue
            
        # USE THE PARSER FOR READING MATERIALS
        questions = extract_reading_content_from_text(full_text, exam_uuid)
        
        exam_title = os.path.splitext(filename)[0]  # Remove extension
        
        # NEW: Use dynamic discipline_id from user selection
        payload = {
            "id": exam_uuid,               # Explicitly set exam ID as UUID
            "title": exam_title,
            "discipline_id": discipline_id,  # Dynamic based on user selection
            "time_limit": 50,
            "source": "singular",          # Mark as singular exam
            "questions": questions
        }
        
        print(f"\n📤 Uploading reading material from file: {file_path}{replacement_note}")
        print(f"📝 Material Title: {exam_title}")
        print(f"📄 File Type: {file_type}")
        print(f"📖 Sections: {len(questions)}")
        print(f"🎯 Discipline: {discipline_name} ({discipline_id})")
        print(f"🔧 Endpoint: /exam/ (singular)")
        print(f"🏷️ Source: singular")
        
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ SUCCESS: {exam_title} - Status: {response.status_code}")
            uploaded_count += 1
        else:
            print(f"❌ FAILED: {exam_title} - Status: {response.status_code}")
            print(f"   Error: {response.text}")
            skipped_count += 1
            
    except Exception as e:
        print(f"💥 Error processing {file_path}: {e}")
        skipped_count += 1

print(f"\n🎉 Upload completed!")
print(f"📊 Summary: {uploaded_count} uploaded, {skipped_count} skipped")
print(f"🎯 Discipline: {discipline_name}")
print(f"📁 Processed from: {folder_path}")