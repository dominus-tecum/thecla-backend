import os
import re
import uuid
from docx import Document
import requests

def extract_questions_from_text(text, exam_uuid):
    questions = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    i = 0
    while i < len(lines):
        q_match = re.match(r'^\d+\.\s+(.*)', lines[i])
        if q_match:
            question_text = q_match.group(1)
            options = []
            i += 1
            
            # Collect options
            while i < len(lines) and re.match(r'^[a-dA-D]\.', lines[i]):
                options.append(re.sub(r'^[a-dA-D]\.\s*', '', lines[i]))
                i += 1
            
            correct_idx = -1
            rationale = None  # NEW: Store rationale
            
            # Find correct answer
            while i < len(lines) and (
                re.match(r'^(?:✅\s*)?(?:Correct\s*)?Answer:', lines[i], re.IGNORECASE)
            ):
                ans_match = re.match(
                    r'^(?:✅\s*)?(?:Correct\s*)?Answer:\s*([a-dA-D])(\.|\,|\s|$)', lines[i], re.IGNORECASE
                )
                if ans_match:
                    correct_letter = ans_match.group(1).lower()
                    correct_idx = ['a', 'b', 'c', 'd'].index(correct_letter)
                    break
                i += 1
            
            # NEW: EXTRACT AND STORE RATIONALE
            if i < len(lines) and lines[i].lower().startswith('rationale:'):
                rationale = lines[i].replace('Rationale:', '').replace('rationale:', '').strip()
                i += 1  # Move past rationale line
            
            if correct_idx == -1:
                print(f"WARNING: No correct answer found for question: '{question_text}'")
            
            questions.append({
                'id': str(uuid.uuid4()),
                'exam_id': exam_uuid,
                'text': question_text,
                'options': options,
                'correct_idx': correct_idx,
                'rationale': rationale  # NEW: Include rationale in payload
            })
        else:
            i += 1
    return questions

# UPDATED PATH FOR GP EXAMS
folder_path = r'd:\Thecla\Training Examinations\GP\Exams\Rationale'
API_URL = 'https://cb46ba37f2c0.ngrok-free.app/exams/'  # Plural endpoint

for filename in os.listdir(folder_path):
    if not filename.lower().endswith('.docx') or filename.startswith('~$'):
        continue
    doc_path = os.path.join(folder_path, filename)
    try:
        exam_uuid = str(uuid.uuid4())  # Generate a UUID for the exam
        document = Document(doc_path)
        full_text = '\n'.join([para.text for para in document.paragraphs])
        questions = extract_questions_from_text(full_text, exam_uuid)
        exam_title = filename.replace('.docx', '')
        payload = {
            "id": exam_uuid,               
            "title": exam_title,
            "discipline_id": "gp",         
            "time_limit": 50,
            "source": "plural",            
            "is_released": False,          
            "questions": questions
        }
        print(f"\n📤 Uploading exam from file: {doc_path}")
        print(f"📝 Exam Title: {exam_title}")
        print(f"❓ Questions: {len(questions)}")
        
        # NEW: Show rationale info
        questions_with_rationale = [q for q in questions if q.get('rationale')]
        print(f"📚 Questions with rationale: {len(questions_with_rationale)}/{len(questions)}")
        
        response = requests.post(API_URL, json=payload)
        if response.status_code == 200:
            print(f"✅ SUCCESS: {exam_title} - Status: {response.status_code}")
            print(f"💡 Remember to release this exam via /admin/exams/{exam_uuid}/release")
        else:
            print(f"❌ FAILED: {exam_title} - Status: {response.status_code}, Response: {response.text}")
            
    except Exception as e:
        print(f"💥 Error processing {doc_path}: {e}")