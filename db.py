import sqlite3
from datetime import datetime

DB_NAME = "tasks.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            assigned_by TEXT NOT NULL,
            assigned_to TEXT NOT NULL,
            deadline TEXT,
            priority TEXT,
            status TEXT DEFAULT 'To Do',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_task(title, description, assigned_by, assigned_to, deadline, priority):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("""
        INSERT INTO tasks (title, description, assigned_by, assigned_to, deadline, priority, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, description, assigned_by, assigned_to, deadline, priority, now, now))
    conn.commit()
    conn.close()

def get_tasks(filter_type, user_email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if filter_type == "assigned_to":
        c.execute("SELECT * FROM tasks WHERE assigned_to=?", (user_email,))
    elif filter_type == "assigned_by":
        c.execute("SELECT * FROM tasks WHERE assigned_by=?", (user_email,))
    else:
        c.execute("SELECT * FROM tasks")
    tasks = c.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, new_status):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE tasks SET status=?, updated_at=? WHERE id=?", (new_status, now, task_id))
    conn.commit()
    conn.close()
