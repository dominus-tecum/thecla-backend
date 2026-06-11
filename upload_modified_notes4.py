import os
import re
import uuid
import base64
from docx import Document
from docx.shared import Inches
import requests
import PyPDF2
from PIL import Image
import io

# ============================
# DEBUG FUNCTIONS
# ============================

def debug_pdf_content(pdf_path):
    """Debug what's actually in the PDF"""
    print(f"\n🔍 DEBUGGING PDF: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return False
    
    file_size = os.path.getsize(pdf_path)
    print(f"   File size: {file_size} bytes ({file_size/1024:.1f} KB)")
    
    try:
        with open(pdf_path, 'rb') as f:
            first_bytes = f.read(20)
            print(f"   File signature (hex): {first_bytes.hex()[:40]}...")
            
            if b'%PDF' in first_bytes:
                print(f"   ✓ Valid PDF signature found")
                pdf_version = first_bytes[5:8].decode('ascii', errors='ignore')
                print(f"   PDF version: {pdf_version}")
            else:
                print(f"   ✗ WARNING: Not a valid PDF file")
                return False
    except Exception as e:
        print(f"   File read error: {e}")
        return False
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            print(f"\n   PyPDF2 Analysis:")
            print(f"   - Pages found: {len(reader.pages)}")
            print(f"   - Is encrypted: {reader.is_encrypted}")
            
            pages_with_text = 0
            total_text_chars = 0
            
            for i in range(min(3, len(reader.pages))):
                text = reader.pages[i].extract_text()
                text_length = len(text.strip())
                total_text_chars += text_length
                
                if text_length > 0:
                    pages_with_text += 1
                    print(f"\n   Page {i+1}: Has text: ✓ ({text_length} characters)")
                else:
                    print(f"\n   Page {i+1}: Has text: ✗ (0 characters)")
            
            print(f"\n   Summary: Pages with text: {pages_with_text}/{min(3, len(reader.pages))}")
            
            if total_text_chars == 0:
                print("   ⚠️  CRITICAL: No text extracted! PDF is likely scanned/image-based")
                return False
            else:
                print("   ✓ Good amount of text extracted")
                return True
                
    except Exception as e:
        print(f"   PyPDF2 error: {e}")
        return False

def debug_docx_content(docx_path):
    """Debug what's in a Word document"""
    print(f"\n🔍 DEBUGGING DOCX: {docx_path}")
    
    try:
        document = Document(docx_path)
        paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
        print(f"   Paragraphs with text: {len(paragraphs)}")
        
        for i, para in enumerate(paragraphs[:5]):
            print(f"   Para {i+1}: '{para[:100]}...'")
        
        images_count = 0
        for rel in document.part.rels.values():
            if "image" in rel.reltype:
                images_count += 1
        print(f"   Images found: {images_count}")
        print(f"   Tables found: {len(document.tables)}")
        
        return True
        
    except Exception as e:
        print(f"   DOCX error: {e}")
        return False

# ============================
# IMAGE EXTRACTION FUNCTIONS
# ============================

def extract_images_from_docx(doc_path, exam_title):
    """Extract images from Word document"""
    try:
        document = Document(doc_path)
        images = []
        image_counter = 1
        
        for rel in document.part.rels.values():
            if "image" in rel.reltype:
                try:
                    image_data = rel.target_part.blob
                    image_filename = f"{exam_title}_image_{image_counter}.png"
                    image_base64 = base64.b64encode(image_data).decode('utf-8')
                    
                    images.append({
                        'filename': image_filename,
                        'data': image_base64,
                        'mimetype': 'image/png'
                    })
                    image_counter += 1
                except Exception as e:
                    print(f"⚠️  Could not extract image: {e}")
                    continue
                    
        print(f"📸 Extracted {len(images)} images from Word document")
        return images
        
    except Exception as e:
        print(f"❌ Error extracting images from Word: {e}")
        return []

def extract_tables_from_docx(document):
    """Extract tables from Word document"""
    tables_data = []
    
    try:
        for table_index, table in enumerate(document.tables):
            table_rows = []
            headers = []
            if table.rows:
                header_cells = table.rows[0].cells
                headers = [cell.text.strip() for cell in header_cells]
            
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells]
                if row_cells:
                    table_rows.append(row_cells)
            
            if table_rows:
                tables_data.append({
                    'headers': headers,
                    'rows': table_rows,
                    'index': table_index
                })
                
        print(f"📊 Extracted {len(tables_data)} tables from Word document")
        return tables_data
        
    except Exception as e:
        print(f"❌ Error extracting tables: {e}")
        return []

def extract_images_from_pdf(pdf_path, exam_title):
    """Extract images from PDF"""
    print(f"   🔍 Extracting images from PDF...")
    return []

def extract_tables_from_pdf(pdf_path):
    """Extract tables from PDF"""
    print("ℹ️  PDF table extraction not implemented")
    return []

# ============================
# TEXT EXTRACTION FUNCTIONS
# ============================

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF files"""
    try:
        print(f"   Extracting text from PDF using PyPDF2...")
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            all_text = ""
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                
                if page_text:
                    all_text += f"\n\n===== Page {page_num + 1} =====\n\n"
                    all_text += page_text
            
            print(f"   Extracted {len(all_text)} characters total")
            return all_text
            
    except Exception as e:
        print(f"❌ Error reading PDF {pdf_path}: {e}")
        return ""

def extract_text_from_docx(docx_path):
    """Extract text from Word document"""
    try:
        document = Document(docx_path)
        paragraphs = [para.text.strip() for para in document.paragraphs if para.text.strip()]
        return '\n\n'.join(paragraphs)
    except Exception as e:
        print(f"❌ Error reading DOCX {docx_path}: {e}")
        return ""

# ============================
# CONTENT PARSING FUNCTIONS
# ============================

def convert_table_to_markdown(table_data):
    """Convert table data to markdown format"""
    if not table_data.get('rows'):
        return ""
    
    markdown_table = ""
    
    if table_data.get('headers'):
        headers = table_data['headers']
        markdown_table += "| " + " | ".join(headers) + " |\n"
        markdown_table += "| " + " | ".join(["---"] * len(headers)) + " |\n"
    else:
        first_row = table_data['rows'][0] if table_data['rows'] else []
        if first_row:
            markdown_table += "| " + " | ".join(first_row) + " |\n"
            markdown_table += "| " + " | ".join(["---"] * len(first_row)) + " |\n"
            table_data['rows'] = table_data['rows'][1:]
    
    for row in table_data.get('rows', []):
        markdown_table += "| " + " | ".join(row) + " |\n"
    
    return markdown_table

def enhance_content_with_media(text_content, images, tables, exam_title):
    """Enhance text content with images and tables"""
    enhanced_content = text_content
    
    for i, table in enumerate(tables, 1):
        table_markdown = convert_table_to_markdown(table)
        if table_markdown:
            table_reference = f"\n\n**Table {i}:**\n\n{table_markdown}"
            enhanced_content += table_reference
    
    return enhanced_content

def preprocess_text_for_parser(text):
    """Add a space to content lines so they don't look like headers"""
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        stripped = line.strip()
        # If line starts with a capital letter and is long (>40 chars)
        if stripped and stripped[0].isupper() and len(stripped) > 40:
            processed_lines.append(' ' + line)
        else:
            processed_lines.append(line)
    
    return '\n'.join(processed_lines)

def parse_general_content(text, exam_uuid):
    """Parse general content (for DOCX files)"""
    sections = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    current_section = None
    current_content = []
    
    for line in lines:
        # FIRST: Check if this is clearly content, not a header
        is_content = False
        
        # Content indicators
        if len(line) > 50:  # Long lines are content
            is_content = True
        elif line[0].isupper() and line.count(' ') > 3 and len(line) > 30:  # Sentence with multiple words
            is_content = True
        elif line.startswith(('A ', 'The ', 'This ', 'As ', 'These ', 'Those ', 'It ', 'There ')):
            is_content = True
        
        if is_content:
            if current_section is not None:
                current_content.append(line)
            continue
        
        # Check if this is a topic/header (YOUR ORIGINAL CODE)
        if len(line) < 100 and line[0].isalpha() and line[0].isupper() and not line.endswith('.'):
            # Save previous section
            if current_section and current_content:
                current_section['options'] = ['\n\n'.join(current_content)]
                sections.append(current_section)
                current_content = []
            
            # Start new section
            current_section = {
                'id': str(uuid.uuid4()),
                'exam_id': exam_uuid,
                'text': line,
                'options': [],
                'correct_idx': -1
            }
        elif current_section is not None:
            current_content.append(line)
        else:
            current_section = {
                'id': str(uuid.uuid4()),
                'exam_id': exam_uuid,
                'text': line[:80] + "..." if len(line) > 80 else line,
                'options': [],
                'correct_idx': -1
            }
            current_content = [line]
    
    if current_section:
        if current_content:
            current_section['options'] = ['\n\n'.join(current_content)]
        sections.append(current_section)
    
    print(f"   Created {len(sections)} sections from general content")
    return sections














def parse_pdf_content(text, exam_uuid):
    """Parse PDF content"""
    sections = []
    pages = re.split(r'===== Page \d+ =====', text)
    
    for page_num, page_content in enumerate(pages, 1):
        if not page_content.strip():
            continue
        
        lines = [line.strip() for line in page_content.split('\n') if line.strip()]
        
        if not lines:
            continue
        
        title = f"Page {page_num}"
        content_lines = []
        
        for line in lines:
            if not line or line.isdigit():
                continue
            
            if (len(line) < 100 and line[0].isalpha() and 
                (line.isupper() or (line[0].isupper() and line[1:].islower())) and
                not line.endswith('.') and not ',' in line):
                title = line
            else:
                content_lines.append(line)
        
        if title == f"Page {page_num}" and content_lines:
            first_line = content_lines[0][:80]
            title = f"Page {page_num}: {first_line}..."
        
        content = '\n\n'.join(content_lines) if content_lines else "Content from PDF page."
        
        sections.append({
            'id': str(uuid.uuid4()),
            'exam_id': exam_uuid,
            'text': title,
            'options': [content],
            'correct_idx': -1
        })
    
    if not sections:
        sections.append({
            'id': str(uuid.uuid4()),
            'exam_id': exam_uuid,
            'text': "PDF Content",
            'options': [text],
            'correct_idx': -1
        })
    
    print(f"   Created {len(sections)} sections from PDF")
    return sections

def extract_reading_content_from_text(text, exam_uuid, source_type="general"):
    """Extract structured content from text"""
    if not text or not text.strip():
        print(f"⚠️  Warning: Empty text content for {source_type}")
        return [{
            'id': str(uuid.uuid4()),
            'exam_id': exam_uuid,
            'text': 'Content Overview',
            'options': ['No text content extracted from document.'],
            'correct_idx': -1
        }]
    
    print(f"   Parsing {len(text)} characters of {source_type} text...")
    
    if source_type == "pdf":
        return parse_pdf_content(text, exam_uuid)
    else:
        return parse_general_content(text, exam_uuid)

def embed_images_directly(text_content, images, exam_title):
    """Embed images directly in content"""
    return text_content

# ============================
# PROFESSION SELECTION
# ============================

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
        '8': ('neonatal_nurse', 'Neonatal Nurse'),
        '9': ('pharmacist', 'Pharmacist')
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
        'neonatal_nurse': r'Neonate\Notes',
        'pharmacist': r'Pharmacist\Notes'
    }
    
    folder = folder_mapping.get(discipline_id, 'Reading Materials')
    full_path = os.path.join(base_path, folder)
    
    if not os.path.exists(full_path):
        print(f"📁 Creating folder: {full_path}")
        os.makedirs(full_path, exist_ok=True)
    
    return full_path

# ============================
# FILE MANAGEMENT FUNCTIONS
# ============================

def check_file_exists_on_server(filename, discipline_id, base_url):
    """Check if a file with the same title already exists on the server"""
    try:
        exam_title = os.path.splitext(filename)[0]
        response = requests.get(f"{base_url}/exams")
        if response.status_code == 200:
            all_exams = response.json()
            for exam in all_exams:
                if exam.get('title') == exam_title and exam.get('discipline_id') == discipline_id:
                    return True, exam.get('id')
        return False, None
    except Exception as e:
        print(f"⚠️  Could not check server for existing files: {e}")
        return False, None

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
            return all_files
        elif choice == '2':
            return select_specific_files(all_files)
        else:
            print("❌ Invalid choice. Please enter 1 or 2")

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
                    print(f"❌ Invalid number: {sel}")
            
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

# ============================
# MAIN UPLOAD SCRIPT
# ============================

BASE_URL = "https://thecla-backend.onrender.com"
API_URL = f'{BASE_URL}/exam/'

discipline_id, discipline_name = get_profession_from_user()
folder_path = get_reading_materials_folder_path(discipline_id)

print(f"\n📁 Scanning folder: {folder_path}")
print(f"🎯 Uploading reading materials for: {discipline_name}")

if not os.path.exists(folder_path):
    print(f"❌ Folder not found: {folder_path}")
    exit()

docx_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.docx') and not f.startswith('~$')]
pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]

all_files = docx_files + pdf_files

if not all_files:
    print(f"❌ No document files found in: {folder_path}")
    exit()

files_to_upload = select_files_to_upload(all_files)

print(f"\n🚀 Ready to upload {len(files_to_upload)} file(s)")

uploaded_count = 0
skipped_count = 0

for filename in files_to_upload:
    file_path = os.path.join(folder_path, filename)
    print(f"\n{'='*60}")
    print(f"PROCESSING: {filename}")
    print(f"{'='*60}")
    
    try:
        if filename.lower().endswith('.pdf'):
            print(f"🔍 Running PDF debug analysis...")
            debug_pdf_content(file_path)
        elif filename.lower().endswith('.docx'):
            print(f"🔍 Running DOCX debug analysis...")
            debug_docx_content(file_path)
        
        file_exists, existing_exam_id = check_file_exists_on_server(filename, discipline_id, BASE_URL)
        
        if file_exists:
            if not confirm_file_replacement(filename):
                print(f"⏭️  Skipping '{filename}' - user chose not to replace")
                skipped_count += 1
                continue
            exam_uuid = existing_exam_id or str(uuid.uuid4())
            replacement_note = " (REPLACING EXISTING)"
        else:
            exam_uuid = str(uuid.uuid4())
            replacement_note = " (NEW)"
        
        exam_title = os.path.splitext(filename)[0]
        
        images = []
        tables = []
        full_text = ""
        
        if filename.lower().endswith('.docx'):
            print(f"📝 Processing Word document...")
            document = Document(file_path)
            full_text = extract_text_from_docx(file_path)
            file_type = "Word Document"
            images = extract_images_from_docx(file_path, exam_title)
            tables = extract_tables_from_docx(document)
            
        elif filename.lower().endswith('.pdf'):
            print(f"📝 Processing PDF document...")
            full_text = extract_text_from_pdf(file_path)
            file_type = "PDF Document"
            images = extract_images_from_pdf(file_path, exam_title)
            tables = extract_tables_from_pdf(file_path)
        
        if not full_text or not full_text.strip():
            print(f"⚠️  WARNING: No text extracted from: {filename}")
            if filename.lower().endswith('.pdf'):
                full_text = f"PDF Document: {exam_title}\n\nThis PDF contains content that requires manual review."
            else:
                full_text = f"Document: {exam_title}\n\nContent extraction may require manual review."
        
        print(f"   Extracted text: {len(full_text)} characters")
        print(f"   Found images: {len(images)}")
        print(f"   Found tables: {len(tables)}")
        
        # ENHANCE CONTENT WITH MEDIA
        if images or tables:
            print(f"🎨 Enhancing content with media...")
            enhanced_text = enhance_content_with_media(full_text, images, tables, exam_title)
        else:
            enhanced_text = full_text
        
        # Preprocess text to fix content lines that look like headers
        enhanced_text = preprocess_text_for_parser(enhanced_text)
        
        image_references = {}
        
        # USE THE PARSER FOR READING MATERIALS
        print(f"📖 Parsing content into structured sections...")
        
        source_type = "pdf" if filename.lower().endswith('.pdf') else "docx"
        questions = extract_reading_content_from_text(enhanced_text, exam_uuid, source_type)
        
        if not questions:
            print(f"⚠️  No content sections extracted from {filename}")
            questions = [{
                'id': str(uuid.uuid4()),
                'exam_id': exam_uuid,
                'text': exam_title,
                'options': ["Content extracted from document. Please view original file for complete content."],
                'correct_idx': -1
            }]
        
        payload = {
            "id": exam_uuid,
            "title": exam_title,
            "discipline_id": discipline_id,
            "time_limit": 50,
            "source": "singular",
            "questions": questions,
            "media_info": {
                "images_count": len(images),
                "tables_count": len(tables),
                "image_references": image_references
            }
        }
        
        print(f"\n📤 UPLOAD SUMMARY:")
        print(f"   File: {filename}{replacement_note}")
        print(f"   Material Title: {exam_title}")
        print(f"   File Type: {file_type}")
        print(f"   Sections: {len(questions)}")
        print(f"   Images: {len(images)}")
        print(f"   Tables: {len(tables)}")
        print(f"   Discipline: {discipline_name} ({discipline_id})")
        
        if questions and questions[0].get('options'):
            first_content = questions[0]['options'][0]
            preview = first_content[:150].replace('\n', ' ')
            print(f"   First section preview: {preview}...")
        
        print(f"\n📤 Uploading to server...")
        response = requests.post(API_URL, json=payload)
        
        if response.status_code == 200:
            print(f"✅ SUCCESS: {exam_title} uploaded successfully!")
            uploaded_count += 1
        else:
            print(f"❌ FAILED: {exam_title} - Status: {response.status_code}")
            print(f"   Error details: {response.text[:200]}...")
            skipped_count += 1
            
    except Exception as e:
        print(f"💥 ERROR processing {filename}: {e}")
        import traceback
        traceback.print_exc()
        skipped_count += 1

print(f"\n{'='*60}")
print(f"🎉 UPLOAD COMPLETED!")
print(f"{'='*60}")
print(f"📊 SUMMARY:")
print(f"   Uploaded: {uploaded_count}")
print(f"   Skipped: {skipped_count}")
print(f"   Total: {uploaded_count + skipped_count}")
print(f"🎯 Discipline: {discipline_name}")
print(f"📁 Processed from: {folder_path}")
print(f"{'='*60}")