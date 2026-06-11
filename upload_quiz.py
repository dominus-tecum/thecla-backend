import os
import re
import uuid
from docx import Document
import requests
import warnings

# Suppress SSL warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class QuizUploader:
    """Smart quiz uploader with duplicate handling"""
    
    def __init__(self, base_url="https://thecla-backend.onrender.com"):
        self.base_url = base_url
        self.endpoints = {
            'create': f"{base_url}/quiz/create",
            'create_or_update': f"{base_url}/quiz/create-or-update",
            'check': f"{base_url}/quiz/check-duplicate"
        }
    
    def check_duplicate(self, title, discipline):
        """Check if quiz already exists"""
        try:
            response = requests.get(
                f"{self.endpoints['check']}?title={title}&discipline={discipline}",
                verify=False,
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('exists', False)
        except Exception as e:
            print(f"⚠️  Could not check for duplicates: {e}")
        return False
    
    def upload_quiz(self, title, discipline, questions):
        """Smart upload: check duplicates and use appropriate endpoint"""
        
        # Check if quiz exists
        is_duplicate = self.check_duplicate(title, discipline)
        
        # Choose endpoint based on duplicate status
        endpoint = self.endpoints['create_or_update'] if is_duplicate else self.endpoints['create']
        operation = "replaced" if is_duplicate else "created"
        
        if is_duplicate:
            print(f"🔄 Duplicate found! Replacing existing quiz: '{title}'")
        else:
            print(f"📤 Creating new quiz: '{title}'")
        
        # Prepare payload
        payload = {
            "title": title,
            "discipline": discipline,
            "questions": questions
        }
        
        # Upload
        try:
            response = requests.post(endpoint, json=payload, verify=False, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Successfully {operation} quiz: {title}")
                print(f"🎯 Quiz ID: {result.get('quiz_id', 'N/A')}")
                print(f"📝 Questions: {result.get('questions_created', len(questions))}")
                return True, operation, result
            else:
                print(f"❌ Failed to {operation} quiz: {response.status_code}")
                print(f"   Error: {response.text}")
                return False, operation, None
                
        except Exception as e:
            print(f"💥 Upload error: {e}")
            return False, operation, None


def extract_questions_from_text(text):
    """Extract questions with multi-line support"""
    questions = []
    lines = [line.rstrip() for line in text.split('\n')]  # Keep empty lines
    i = 0
    question_count = 0
    
    print(f"📄 Processing {len(lines)} lines of text...")
    
    while i < len(lines):
        q_match = re.match(r'^\d+\.\s+(.*)', lines[i])
        if q_match:
            question_count += 1
            question_text = q_match.group(1)
            options = []
            i += 1
            
            # 🟢 MULTI-LINE QUESTION TEXT
            while i < len(lines) and lines[i].strip() and not re.match(r'^[a-dA-D][\.\)]', lines[i]):
                question_text += " " + lines[i].strip()
                i += 1
            
            # 🟢 MULTI-LINE OPTIONS
            option_count = 0
            while i < len(lines) and re.match(r'^[a-dA-D][\.\)]', lines[i]):
                option_text = re.sub(r'^[a-dA-D][\.\)]\s*', '', lines[i])
                i += 1
                
                # Continue reading multi-line option text
                while (i < len(lines) and lines[i].strip() and 
                       not re.match(r'^[a-dA-D][\.\)]', lines[i]) and
                       not re.match(r'^(?:✅\s*)?(?:Correct\s*)?Answer:', lines[i], re.IGNORECASE) and
                       'rationale:' not in lines[i].lower()):
                    option_text += " " + lines[i].strip()
                    i += 1
                
                options.append(option_text.strip())
                option_count += 1
            
            print(f"   Found question {question_count} with {option_count} options")
            
            correct_idx = -1
            rationale = None
            
            # Skip blank lines
            while i < len(lines) and not lines[i].strip():
                i += 1
            
            # Find correct answer
            if i < len(lines) and re.match(r'^(?:✅\s*)?(?:Correct\s*)?Answer:', lines[i], re.IGNORECASE):
                ans_match = re.match(
                    r'^(?:✅\s*)?(?:Correct\s*)?Answer:\s*([a-dA-D])(?:\.|\)|\s|$)', lines[i], re.IGNORECASE
                )
                if ans_match:
                    correct_letter = ans_match.group(1).lower()
                    if correct_letter in ['a', 'b', 'c', 'd']:
                        correct_idx = ['a', 'b', 'c', 'd'].index(correct_letter)
                i += 1
            
            # Skip blank lines
            while i < len(lines) and not lines[i].strip():
                i += 1
            
            # 🟢 MULTI-LINE RATIONALE
            if i < len(lines) and 'rationale:' in lines[i].lower():
                rationale_parts = []
                rationale_text = lines[i].split('rationale:', 1)[-1].split('Rationale:', 1)[-1].strip()
                if rationale_text:
                    rationale_parts.append(rationale_text)
                i += 1
                
                # Continue reading multi-line rationale
                while (i < len(lines) and lines[i].strip() and 
                       not re.match(r'^\d+\.\s+', lines[i])):
                    rationale_parts.append(lines[i].strip())
                    i += 1
                
                rationale = " ".join(rationale_parts)
            
            # 🟢 AUTO-DETECT TOPIC
            topic = auto_detect_topic(question_text)
            
            # Validate question
            if len(options) >= 2 and 0 <= correct_idx < len(options):
                questions.append({
                    'text': question_text.strip(),
                    'options': [opt.strip() for opt in options],
                    'correct_idx': correct_idx,
                    'rationale': rationale,
                    'topic': topic,
                    'subtopic': '',
                    'difficulty': auto_detect_difficulty(question_text, options)
                })
                
                if question_count <= 3:
                    print(f"📝 Question #{question_count}: {question_text[:60]}...")
                    print(f"   Topic: {topic}, Correct: {['A','B','C','D'][correct_idx]}")
            else:
                print(f"⚠️  Skipping invalid question #{question_count}")
        
        else:
            i += 1
    
    print(f"🎯 Total valid questions extracted: {len(questions)}")
    return questions


def auto_detect_topic(question_text):
    """Automatically detect topic for Smart Quiz"""
    text_lower = question_text.lower()
    
    topic_keywords = {
        "pharmacology": ["medication", "drug", "dose", "prescription", "side effect", "contraindication",
                        "antibiotic", "analgesic", "therapeutic", "interaction", "overdose", "administration",
                        "dosage", "adverse", "toxicity", "pharmacology", "pharmacokinetic", "warfarin", "insulin",
                        "pharmacy", "formulation", "compounding", "dispensing", "medicinal", "drug interaction",
                        "drug therapy", "clinical pharmacy", "pharmaceutics", "biopharmaceutics", "pharmacogenomics"],
        "anatomy": ["anatomy", "organ", "bone", "muscle", "nerve", "artery", "vein", "heart", "lung",
                   "liver", "kidney", "brain", "spinal", "joint", "tissue", "structure"],
        "physiology": ["physiology", "function", "metabolism", "hormone", "system", "process", "mechanism",
                      "homeostasis", "regulation", "secretion", "absorption", "circulation", "respiration"],
        "clinical_skills": ["assess", "examine", "procedure", "technique", "skill", "examination", "assessment",
                           "diagnostic", "evaluate", "monitor", "observe", "palpate", "auscultate"],
        "patient_care": ["care", "nursing", "patient", "comfort", "hygiene", "support", "education", "teaching",
                        "communication", "counseling", "recovery", "rehabilitation", "discharge"],
        "medical_ethics": ["ethics", "consent", "confidential", "rights", "legal", "ethical", "privacy", "autonomy",
                          "beneficence", "non-maleficence", "justice", "dilemma", "decision"],
        "emergency_care": ["emergency", "critical", "urgent", "resuscitation", "triage", "crisis", "acute",
                          "life-threatening", "cardiac arrest", "shock", "trauma"],
        "diagnosis": ["diagnosis", "diagnose", "test", "result", "interpret", "finding", "symptom", "sign",
                     "laboratory", "imaging", "x-ray", "blood test", "diagnostic"],
        "pharmacy_law": ["law", "legal", "regulation", "controlled substance", "dea", "fda", "compliance",
                        "prescription law", "drug scheduling", "professional regulation"],
        "pharmacy_management": ["inventory", "management", "supply chain", "procurement", "storage",
                               "quality control", "pharmacy administration", "business management"]
    }
    
    for topic, keywords in topic_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return topic
    
    return "general"


def auto_detect_difficulty(question_text, options):
    """Auto-detect question difficulty"""
    text_length = len(question_text)
    word_count = len(question_text.split())
    
    if word_count < 15 or text_length < 100:
        return "basic"
    elif word_count < 30 or text_length < 200:
        return "intermediate"
    else:
        return "advanced"


def get_profession_from_user():
    """Get profession selection from user"""
    disciplines = {
        '1': ('gp', 'General Practitioner'),
        '2': ('nurse', 'Nurse'),
        '3': ('midwife', 'Midwife'),
        '4': ('lab_tech', 'Lab Technologist'),
        '5': ('physiotherapist', 'Physiotherapist'),
        '6': ('icu_nurse', 'ICU Nurse'),
        '7': ('emergency_nurse', 'Emergency Nurse'),
        '8': ('neonatal_nurse', 'Neonatal Nurse'),
        '9': ('pharmacist', 'Pharmacist')  # NEW
    }
    
    print("\n🎯 SELECT PROFESSION FOR QUIZ UPLOAD:")
    print("=" * 50)
    for key, (discipline_id, discipline_name) in disciplines.items():
        print(f"   {key}. {discipline_name} ({discipline_id})")
    print("=" * 50)
    
    while True:
        choice = input("\nEnter your choice (1-9): ").strip()  # UPDATED: 1-9
        if choice in disciplines:
            discipline_id, discipline_name = disciplines[choice]
            print(f"✅ Selected: {discipline_name} (discipline: {discipline_id})")
            return discipline_id, discipline_name
        else:
            print("❌ Invalid choice. Please enter a number between 1-9")  # UPDATED


def get_folder_path(discipline_id):
    """Get folder path for discipline"""
    base_path = r'd:\Thecla\Training Examinations'
    
    folder_mapping = {
        'gp': r'GP\Exams\Quiz',
        'nurse': r'Nurses\Prometric Exam\Quiz',
        'midwife': r'Midwives\Quiz',
        'lab_tech': r'Lab Technologists\Quiz',
        'physiotherapist': r'Physiotherapists\Quiz',
        'icu_nurse': r'Specialty Nurses\ICU\Quiz',
        'emergency_nurse': r'Specialty Nurses\Emergency\Quiz',
        'neonatal_nurse': r'Specialty Nurses\Neonatal\Quiz',
        'pharmacist': r'Pharmacist\Quiz'  # NEW
    }
    
    folder = folder_mapping.get(discipline_id, 'Exams')
    full_path = os.path.join(base_path, folder)
    
    if not os.path.exists(full_path):
        print(f"📁 Creating folder: {full_path}")
        os.makedirs(full_path, exist_ok=True)
    
    return full_path


def process_exam_file(filename, folder_path, discipline, discipline_name):
    """Process and upload a single exam file"""
    doc_path = os.path.join(folder_path, filename)
    
    try:
        # Read document
        document = Document(doc_path)
        full_text = '\n'.join([para.text for para in document.paragraphs])
        
        print(f"\n{'='*60}")
        print(f"🔍 PROCESSING: {filename}")
        print(f"{'='*60}")
        
        # Extract questions
        questions = extract_questions_from_text(full_text)
        
        if not questions:
            print(f"❌ No valid questions found")
            return False
        
        # Get quiz title
        quiz_title = filename.replace('.docx', '')
        
        print(f"\n📊 Quiz Summary:")
        print(f"   Title: {quiz_title}")
        print(f"   Discipline: {discipline_name} ({discipline})")
        print(f"   Questions: {len(questions)}")
        
        # Show topic distribution
        topics = {}
        for q in questions:
            topic = q.get('topic', 'unknown')
            topics[topic] = topics.get(topic, 0) + 1
        print(f"   Topics: {', '.join([f'{k}({v})' for k, v in topics.items()])}")
        
        # Initialize uploader
        uploader = QuizUploader()
        
        # Smart upload
        success, operation, result = uploader.upload_quiz(
            title=quiz_title,
            discipline=discipline,
            questions=questions
        )
        
        return success
        
    except Exception as e:
        print(f"💥 Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def upload_single_exam():
    """Upload single exam"""
    print("\n🎯 SINGLE EXAM UPLOAD")
    print("=" * 40)
    
    discipline, discipline_name = get_profession_from_user()
    folder_path = get_folder_path(discipline)
    
    # List files
    docx_files = [f for f in os.listdir(folder_path) 
                  if f.lower().endswith('.docx') and not f.startswith('~$')]
    
    if not docx_files:
        print(f"❌ No .docx files found")
        return
    
    print(f"\n📄 Available exams:")
    for i, filename in enumerate(docx_files, 1):
        print(f"   {i}. {filename}")
    
    # Get user selection
    while True:
        try:
            choice = input(f"\nSelect file (1-{len(docx_files)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(docx_files):
                filename = docx_files[idx]
                break
            else:
                print(f"❌ Enter 1-{len(docx_files)}")
        except ValueError:
            print("❌ Enter a number")
    
    # Process file
    process_exam_file(filename, folder_path, discipline, discipline_name)


def upload_all_exams():
    """Upload all exams in folder"""
    print("\n🎯 BATCH UPLOAD")
    print("=" * 40)
    
    discipline, discipline_name = get_profession_from_user()
    folder_path = get_folder_path(discipline)
    
    docx_files = [f for f in os.listdir(folder_path) 
                  if f.lower().endswith('.docx') and not f.startswith('~$')]
    
    if not docx_files:
        print(f"❌ No .docx files found")
        return
    
    print(f"\n📄 Found {len(docx_files)} file(s)")
    
    successful = 0
    failed = 0
    
    for filename in docx_files:
        print(f"\n{'='*60}")
        print(f"📋 Processing: {filename}")
        
        if process_exam_file(filename, folder_path, discipline, discipline_name):
            successful += 1
        else:
            failed += 1
    
    print(f"\n{'='*60}")
    print("📊 SUMMARY")
    print(f"{'='*60}")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📄 Total: {len(docx_files)}")


def main():
    """Main menu"""
    print("\n🎯 SMART QUIZ UPLOADER")
    print("=" * 50)
    print("1. Upload Single Exam")
    print("2. Upload All Exams")
    print("3. Exit")
    print("=" * 50)
    
    while True:
        choice = input("\nSelect (1-3): ").strip()
        if choice == '1':
            upload_single_exam()
            break
        elif choice == '2':
            upload_all_exams()
            break
        elif choice == '3':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Enter 1, 2, or 3")


if __name__ == "__main__":
    main()