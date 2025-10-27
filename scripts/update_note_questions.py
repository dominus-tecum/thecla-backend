import sqlite3
import sys
import os
import json

# === CONFIGURE THESE ===
DB = r"D:\theclamed\backend\app\theclamed.db"
NOTE_ID = "63bc75c4-41b9-4345-b8fc-27e2e98c381f"
QUESTIONS_FILE = r"D:\theclamed\backend\app\questions.json"  # path to your 50-question JSON file
# ========================

if not os.path.exists(DB):
    print("ERROR: DB not found:", DB); sys.exit(1)
if not os.path.exists(QUESTIONS_FILE):
    print("ERROR: questions file not found:", QUESTIONS_FILE); sys.exit(2)

with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
    questions_json = f.read()

# (Optional) validate JSON is an array
try:
    parsed = json.loads(questions_json)
    if not isinstance(parsed, list):
        print("ERROR: questions JSON must be a top-level array of question objects."); sys.exit(3)
except Exception as e:
    print("ERROR: questions file is not valid JSON:", e); sys.exit(4)

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Ensure column exists
cur.execute("PRAGMA table_info(notes);")
cols = [r[1] for r in cur.fetchall()]
if "questions" not in cols:
    try:
        cur.execute("ALTER TABLE notes ADD COLUMN questions TEXT;")
        conn.commit()
        print("Added questions column to notes.")
    except Exception as e:
        print("WARN: failed to add column:", e)

# Update the specific note with the raw JSON text (stored as TEXT)
cur.execute("BEGIN;")
cur.execute("UPDATE notes SET questions = ? WHERE id = ?", (questions_json, NOTE_ID))
affected = cur.rowcount
cur.execute("COMMIT;")
conn.commit()
conn.close()

if affected == 0:
    print("WARNING: no note updated — check NOTE_ID is correct.")
else:
    print(f"Updated note {NOTE_ID} with questions (rows affected: {affected}).")