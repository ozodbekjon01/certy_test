# db_create.py
# SQLite database creator for your CBT / exam system

import sqlite3
from werkzeug.security import generate_password_hash

DB_NAME = "database.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# =========================
# USERS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    tg_id integer,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# =========================
# TESTS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    bio TEXT,
    image_location TEXT
)
""")

# =========================
# QUESTIONS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL,
    question_type TEXT NOT NULL,
    question TEXT NOT NULL,
    image_location TEXT,
    audio_location TEXT,
    video_link TEXT,
    question_translate TEXT,
    comment TEXT,

    FOREIGN KEY (test_id)
        REFERENCES tests(id)
        ON DELETE CASCADE
)
""")

# =========================
# OPTIONS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    option TEXT NOT NULL,
    option_translate TEXT,
    image_location TEXT,
    audio_location TEXT,
    is_correct INTEGER DEFAULT 0,
    appropriate TEXT,
    appropriate_translate TEXT,

    FOREIGN KEY (question_id)
        REFERENCES questions(id)
        ON DELETE CASCADE
)
""")

# =========================
# OFFERS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_name TEXT NOT NULL,
    offer_time INTEGER NOT NULL,
    price REAL NOT NULL,
    discount REAL DEFAULT 0
)
""")

# =========================
# OFFER TESTS
# Many-to-many relation
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS offer_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id INTEGER NOT NULL,
    test_id INTEGER NOT NULL,

    FOREIGN KEY (offer_id)
        REFERENCES offers(id)
        ON DELETE CASCADE,

    FOREIGN KEY (test_id)
        REFERENCES tests(id)
        ON DELETE CASCADE
)
""")

# =========================
# CONTRACTS
# User subscriptions/purchases
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    offer_id INTEGER NOT NULL,
    contract_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (offer_id)
        REFERENCES offers(id)
        ON DELETE CASCADE
)
""")

# =========================
# ATTEMPTS
# User exam results
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    test_id INTEGER NOT NULL,
    score INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    wrong_answers INTEGER DEFAULT 0,
    percentage REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (test_id)
        REFERENCES tests(id)
        ON DELETE CASCADE
)
""")

# =========================
# INDEXES
# =========================
cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_questions_test_id
ON questions(test_id)
""")

# cursor.execute("""
# CREATE INDEX IF NOT EXISTS idx_options_question_id
# ON options(question_id)
# """)

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_offer_tests_offer_id
ON offer_tests(offer_id)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_offer_tests_test_id
ON offer_tests(test_id)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_contracts_user_id
ON contracts(user_id)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_contracts_offer_id
ON contracts(offer_id)
""")

cursor.execute("""
CREATE INDEX IF NOT EXISTS idx_attempts_user_id
ON attempts(user_id)
""")


# Add default admin
cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
if not cursor.fetchone():
    cursor.execute("""insert into users (username, tg_id, password_hash, role) values (?, ?, ?, ?)""",
                   ("admin", None, generate_password_hash("admin123"), "admin"))

conn.commit()
conn.close()

print(f"Database '{DB_NAME}' created and initialized successfully.")