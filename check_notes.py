import requests

BASE_URL = "https://thecla-backend.onrender.com"

# Get all exams (these are actually the notes/reading materials in your system)
response = requests.get(f"{BASE_URL}/exams")
if response.status_code == 200:
    exams = response.json()
    
    print("="*60)
    print("ALL READING MATERIALS IN DATABASE:")
    print("="*60)
    
    for exam in exams:
        print(f"\n📚 Title: {exam.get('title')}")
        print(f"   Discipline: {exam.get('discipline_id')}")
        print(f"   Source: {exam.get('source')}")
        print(f"   Questions: {len(exam.get('questions', []))}")
        
        if exam.get('questions'):
            q = exam['questions'][0]
            print(f"   Question keys: {list(q.keys())}")
            print(f"   Question text preview: {q.get('text', '')[:100]}")
            
            if q.get('options'):
                print(f"   Options[0] length: {len(q['options'][0]) if q['options'][0] else 0}")
                print(f"   Options[0] preview: {q['options'][0][:100] if q['options'][0] else 'EMPTY'}")
            else:
                print(f"   Options: EMPTY")
                
            if q.get('content'):
                print(f"   Content field found! Length: {len(q['content'])}")
                
        print("-"*40)
else:
    print(f"Failed to fetch: {response.status_code}")