import os
import re
import uuid
from docx import Document
import requests

# ADD PDF SUPPORT
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    print("⚠️ pdfplumber not installed. PDF files will be skipped.")
    print("💡 Run: pip install pdfplumber")
    PDF_SUPPORT = False

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

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF files"""
    if not PDF_SUPPORT:
        print("❌ PDF support not available. Install pdfplumber.")
        return ""
    
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        return full_text
    except Exception as e:
        print(f"❌ Error extracting text from PDF: {e}")
        return ""

def extract_text_from_docx(docx_path):
    """Extract text from Word files"""
    try:
        document = Document(docx_path)
        return '\n'.join([para.text for para in document.paragraphs])
    except Exception as e:
        print(f"❌ Error extracting text from Word file: {e}")
        return ""

# UPDATED PATH FOR GP EXAMS
folder_path = r'd:\Thecla\Training Examinations\GP\Study Notes'
API_URL = 'https://cb46ba37f2c0.ngrok-free.app/exam/'  # Singular endpoint

print(f"🔍 Checking folder: {folder_path}")

# Check if folder exists and list files
if not os.path.exists(folder_path):
    print(f"❌ Folder does not exist: {folder_path}")
    exit(1)

files = os.listdir(folder_path)
print(f"📁 Found {len(files)} files in folder:")
for file in files:
    print(f"   - {file}")

# Process both DOCX and PDF files
for filename in os.listdir(folder_path):
    file_path = os.path.join(folder_path, filename)
    
    # Skip system files and unsupported formats
    if filename.startswith('~$'):
        continue
        
    # Skip if not DOCX or PDF
    if not (filename.lower().endswith('.docx') or filename.lower().endswith('.pdf')):
        continue
        
    try:
        exam_uuid = str(uuid.uuid4())
        full_text = ""
        file_type = ""
        
        # Handle different file types
        if filename.lower().endswith('.docx'):
            full_text = extract_text_from_docx(file_path)
            file_type = "Word"
        elif filename.lower().endswith('.pdf'):
            full_text = extract_text_from_pdf(file_path)
            file_type = "PDF"
        
        if not full_text.strip():
            print(f"⚠️ No text extracted from: {filename}")
            continue
            
        # USE THE READING CONTENT PARSER
        questions = extract_reading_content_from_text(full_text, exam_uuid)
        
        exam_title = filename.replace('.docx', '').replace('.pdf', '')
        payload = {
            "id": exam_uuid,
            "title": exam_title,
            "discipline_id": "gp",
            "time_limit": 50,
            "source": "singular",
            "questions": questions
        }
        print(f"\n📤 Uploading {file_type} file: {filename}")
        print(f"📝 Material Title: {exam_title}")
        print(f"📖 Sections: {len(questions)}")
        print(f"🎯 Discipline: gp")
        print(f"🔧 Endpoint: /exam/ (singular)")
        print(f"🏷️ Source: singular")
        
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ SUCCESS: {exam_title} - Status: {response.status_code}")
        else:
            print(f"❌ FAILED: {exam_title} - Status: {response.status_code}, Response: {response.text}")
            
    except Exception as e:
        print(f"💥 Error processing {file_path}: {e}")

print("\n🎉 Processing complete!")