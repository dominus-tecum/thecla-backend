# update_config.py
import requests

API_URL = 'https://420f6f74b2f1.ngrok-free.app'

# Update config to match your existing "Exam 6"
config_payload = {
    "exam_type": "custom",
    "time_per_question": 1.5,
    "total_questions": 50  # Matches your actual 50 questions
}

response = requests.post(f'{API_URL}/keamedexam/config', json=config_payload)

if response.status_code == 200:
    print("✅ Config updated successfully!")
    print("📱 'Exam 6' should now appear in KeamedExamCenter")
else:
    print(f"❌ Failed: {response.status_code} - {response.text}")