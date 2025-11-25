CREATE TABLE keamedexam_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    user_name TEXT NOT NULL,
    user_profession TEXT,
    exam_type TEXT NOT NULL,
    exam_id TEXT NOT NULL,
    exam_title TEXT NOT NULL,
    score INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    time_spent INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_answers TEXT,
    topic_performance TEXT
);

CREATE TABLE keamedexam_config (
    exam_type TEXT PRIMARY KEY,
    time_per_question REAL NOT NULL,
    total_questions INTEGER NOT NULL
);

INSERT INTO keamedexam_config (exam_type, time_per_question, total_questions) VALUES
('nclex_rn', 1.5, 145),
('nclex_pn', 1.5, 85),
('custom', 2.0, 50);