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
            
        # Detect section headers (numbered items, bold text, or titles)
        is_header = (
            re.match(r'^\d+\.\s+', line) or                    # "1. Title"
            re.match(r'^[A-Z][A-Za-z\s]+:', line) or          # "Section Title:"
            re.match(r'^[A-Z\s]{5,}', line) or                # "ALL CAPS TITLE"
            (len(line) < 100 and not line.endswith('.')) or   # Short lines without periods
            re.match(r'^[IVX]+\.', line) or                   # "I.", "II.", "III."
            re.match(r'^\([a-zA-Z]\)', line)                  # "(a)", "(b)", etc.
        )
        
        if is_header:
            # Save previous section if exists
            if current_section and (current_section['text'] or current_section['options']):
                sections.append(current_section)
            
            # Start new section
            current_section = {
                'id': str(uuid.uuid4()),
                'exam_id': exam_uuid,
                'text': line,  # This is the section title/header
                'options': [],  # This will store the content paragraphs
                'correct_idx': -1
            }
        
        # If we're in a section and this line is content
        elif current_section is not None:
            # Add the line as content (paragraph)
            current_section['options'].append(line)
        
        # If no section started yet, create one with the first line as title
        elif current_section is None:
            current_section = {
                'id': str(uuid.uuid4()),
                'exam_id': exam_uuid,
                'text': "Content Overview",  # Default title
                'options': [line],  # First line as content
                'correct_idx': -1
            }
    
    # Don't forget the last section
    if current_section and (current_section['text'] or current_section['options']):
        sections.append(current_section)
    
    # If no sections found, treat everything as one section
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

# MAIN UPLOAD SCRIPT FOR READING MATERIALS
API_URL = 'https://cb46ba37f2c0.ngrok-free.app/exam/'  # Singular endpoint

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

print(f"📄 Found {len(all_files)} document file(s) to process:")
print(f"   - Word documents: {len(docx_files)}")
print(f"   - PDF files: {len(pdf_files)}")

for filename in all_files:
    file_path = os.path.join(folder_path, filename)
    try:
        exam_uuid = str(uuid.uuid4())  # Generate a UUID for the exam
        
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
            continue
        
        if not full_text.strip():
            print(f"⚠️  No text extracted from: {filename}")
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
        
        print(f"\n📤 Uploading reading material from file: {file_path}")
        print(f"📝 Material Title: {exam_title}")
        print(f"📄 File Type: {file_type}")
        print(f"📖 Sections: {len(questions)}")
        print(f"🎯 Discipline: {discipline_name} ({discipline_id})")
        print(f"🔧 Endpoint: /exam/ (singular)")
        print(f"🏷️ Source: singular")
        
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ SUCCESS: {exam_title} - Status: {response.status_code}")
        else:
            print(f"❌ FAILED: {exam_title} - Status: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"💥 Error processing {file_path}: {e}")

print(f"\n🎉 Reading materials upload completed for {discipline_name}!")
print(f"📁 Files were processed from: {folder_path}")