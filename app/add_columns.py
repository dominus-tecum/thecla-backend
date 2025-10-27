import sqlite3, os
db = r'D:/TheclaMed/backend/app/theclamed.db'
if not os.path.exists(db):
    print("DB not found:", db)
else:
    conn = sqlite3.connect(db)
    c = conn.cursor()
    for sql in (
        "ALTER TABLE notes ADD COLUMN s3_key TEXT",
        "ALTER TABLE notes ADD COLUMN thumbnail_s3_key TEXT"
    ):
        try:
            c.execute(sql)
            print("Executed:", sql)
        except Exception as e:
            print("Skipped/failed:", sql, "->", e)
    conn.commit()
    conn.close()
    print("Done")