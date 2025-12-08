import os
import re
import uuid
from docx import Document
import requests

# 🟢 CORRECT: Use plural exams endpoint for Smart Quiz
API_URL = 'https://25d32be38252.ngrok-free.app/quiz/create'


def extract_questions_from_text(text, exam_uuid):
    questions = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]
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
            
            # Collect options
            option_count = 0  # ✅ Define option_count here
            while i < len(lines) and re.match(r'^[a-dA-D][\.\)]', lines[i]):
                option_text = re.sub(r'^[a-dA-D][\.\)]\s*', '', lines[i])
                options.append(option_text)
                option_count += 1
                i += 1
            
            print(f"   Found question {question_count} with {option_count} options")  # ✅ Now option_count is defined
            
            correct_idx = -1
            rationale = None
            
            # Find correct answer
            while i < len(lines) and (
                re.match(r'^(?:✅\s*)?(?:Correct\s*)?Answer:', lines[i], re.IGNORECASE)
            ):
                ans_match = re.match(
                    r'^(?:✅\s*)?(?:Correct\s*)?Answer:\s*([a-dA-D])(?:\.|\)|\s|$)', lines[i], re.IGNORECASE
                )
                if ans_match:
                    correct_letter = ans_match.group(1).lower()
                    correct_idx = ['a', 'b', 'c', 'd'].index(correct_letter)
                    i += 1
                    break
                i += 1
            
            # Extract rationale
            if i < len(lines) and 'rationale:' in lines[i].lower():
                rationale_line = lines[i]
                rationale = rationale_line.split('Rationale:', 1)[-1].split('rationale:', 1)[-1].strip()
                i += 1
            
            # 🟢 AUTO-DETECT TOPIC for Smart Quiz
            topic = auto_detect_topic(question_text)
            
            questions.append({
                'text': question_text,
                'options': options,
                'correct_idx': correct_idx,
                'rationale': rationale,
                'topic': topic,  # 🟢 REQUIRED FOR SMART QUIZ
                'subtopic': '',  
                'difficulty': auto_detect_difficulty(question_text, options)
            })
            
            print(f"📝 Question #{question_count}: {question_text[:50]}...")
            print(f"   Topic: {topic}")
            print(f"   Correct answer: {correct_idx}")
            
        else:
            i += 1
    
    print(f"🎯 Total questions extracted: {len(questions)}")
    return questions

def auto_detect_topic(question_text):
    """Automatically detect topic for Smart Quiz"""
    text_lower = question_text.lower()
    
    topic_keywords = {
        "pharmacology": ["medication", "drug", "dose", "prescription", "side effect", "contraindication",
                        "antibiotic", "analgesic", "therapeutic", "interaction", "overdose", "administration",
                        "dosage", "adverse", "toxicity", "pharmacology", "pharmacokinetic", "warfarin", "insulin"],
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
                     "laboratory", "imaging", "x-ray", "blood test", "diagnostic"]
    }
    
    for topic, keywords in topic_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            return topic
    
    return "general"

def auto_detect_difficulty(question_text, options):
    text_length = len(question_text)
    word_count = len(question_text.split())
    
    if word_count < 15 or text_length < 100:
        return "basic"
    elif word_count < 30 or text_length < 200:
        return "intermediate"
    else:
        return "advanced"

def get_profession_from_user():
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
    
    print("\n🎯 SELECT PROFESSION FOR QUIZ UPLOAD:")
    print("=" * 50)
    for key, (discipline_id, discipline_name) in disciplines.items():
        print(f"   {key}. {discipline_name} ({discipline_id})")
    print("=" * 50)
    
    while True:
        choice = input("\nEnter your choice (1-8): ").strip()
        if choice in disciplines:
            discipline_id, discipline_name = disciplines[choice]
            print(f"✅ Selected: {discipline_name} (discipline: {discipline_id})")
            return discipline_id, discipline_name
        else:
            print("❌ Invalid choice. Please enter a number between 1-8")

def get_folder_path(discipline_id):
    base_path = r'd:\Thecla\Training Examinations'
    
    folder_mapping = {
        'gp': r'GP\Exams\Quiz',
        'nurse': r'Nurses\Prometric Exam\Quiz',
        'midwife': r'Midwives\Exams',
        'lab_tech': r'Lab Technologists\Exams',
        'physiotherapist': r'Physiotherapists\Exams',
        'icu_nurse': r'Specialty Nurses\ICU\Exams',
        'emergency_nurse': r'Specialty Nurses\Emergency\Exams',
        'neonatal_nurse': r'Specialty Nurses\Neonatal\Exams'
    }
    
    folder = folder_mapping.get(discipline_id, 'Exams')
    full_path = os.path.join(base_path, folder)
    
    if not os.path.exists(full_path):
        print(f"📁 Creating folder: {full_path}")
        os.makedirs(full_path, exist_ok=True)
    
    return full_path

def process_exam_file(filename, folder_path, discipline, discipline_name):
    """Process and upload a single exam file for Smart Quiz"""
    doc_path = os.path.join(folder_path, filename)
    try:
        document = Document(doc_path)
        full_text = '\n'.join([para.text for para in document.paragraphs])
        
        print(f"\n🔍 PROCESSING EXAM: {filename}")
        print("=" * 50)
        
        exam_uuid = str(uuid.uuid4())
        questions = extract_questions_from_text(full_text, exam_uuid)
        exam_title = filename.replace('.docx', '')
        
        # 🟢 CORRECTED: Proper payload format for Smart Quiz
        payload = {
            "title": exam_title,
            "discipline": discipline,  # ✅ This matches your backend
            "questions": [
                {
                    "text": q["text"],
                    "options": q["options"],
                    "correct_idx": q["correct_idx"],
                    "rationale": q.get("rationale", ""),
                    "topic": q.get("topic", "general"),  # ✅ REQUIRED for Smart Quiz
                    "subtopic": q.get("subtopic", ""),
                    "difficulty": q.get("difficulty", "intermediate")
                }
                for q in questions
            ]
        }
       
        print(f"\n📤 Uploading {discipline_name} exam: {exam_title}")
        print(f"🎯 Discipline: {discipline_name} ({discipline})")
        print(f"❓ Questions: {len(questions)}")
        print(f"📊 Topics: {set(q.get('topic', 'general') for q in questions)}")
        
        # Debug: Show first question structure
        if questions:
            first_q = questions[0]
            print(f"🔍 Sample question: {first_q['text'][:50]}...")
            print(f"   Options: {len(first_q['options'])}")
            print(f"   Correct index: {first_q['correct_idx']}")
            print(f"   Topic: {first_q.get('topic', 'MISSING')}")
        
        # 🟢 Upload to quiz endpoint
        response = requests.post(API_URL, json=payload, verify=False, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ SUCCESS: {exam_title}")
            print(f"🎯 Quiz ID: {result.get('quiz_id', result.get('exam_id', 'N/A'))}")
            print(f"📝 Questions created: {result.get('questions_created', len(questions))}")
            print(f"🚀 READY FOR SMART QUIZ!")
        else:
            print(f"❌ FAILED: {exam_title} - Status: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"💥 Error processing {doc_path}: {e}")
        import traceback
        traceback.print_exc()


def upload_single_exam():
    print("\n🎯 SINGLE EXAM UPLOAD (for Smart Quiz)")
    print("=" * 40)
    
    discipline, discipline_name = get_profession_from_user()
    folder_path = get_folder_path(discipline)
    
    docx_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.docx') and not f.startswith('~$')]
    
    if not docx_files:
        print(f"❌ No .docx files found in: {folder_path}")
        return
    
    print(f"\n📄 Available exams in {discipline_name} folder:")
    for i, filename in enumerate(docx_files, 1):
        print(f"   {i}. {filename}")
    
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
    
    process_exam_file(filename, folder_path, discipline, discipline_name)

def upload_all_exams():
    discipline, discipline_name = get_profession_from_user()
    folder_path = get_folder_path(discipline)

    print(f"\n📁 Scanning folder: {folder_path}")
    print(f"🎯 Uploading exams for Smart Quiz: {discipline_name}")

    if not os.path.exists(folder_path):
        print(f"❌ Folder not found: {folder_path}")
        return

    docx_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.docx') and not f.startswith('~$')]

    if not docx_files:
        print(f"❌ No .docx files found in: {folder_path}")
        return

    print(f"📄 Found {len(docx_files)} exam file(s) to process")

    for filename in docx_files:
        process_exam_file(filename, folder_path, discipline, discipline_name)

    print(f"\n🎉 Smart Quiz exam upload completed for {discipline_name}!")
    print("🚀 Your exams are now ready for Smart Quiz generation!")

def main():
    print("🎯 SMART QUIZ EXAM UPLOAD MANAGER")
    print("=" * 50)
    print("1. Upload a Specific Exam (for Smart Quiz)")
    print("2. Upload All Exams in Folder (Batch)")
    print("3. Exit")
    print("=" * 50)
    
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