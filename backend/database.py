import sqlite3

def get_connection():
    conn = sqlite3.connect("admin.db", check_same_thread=False)
    return conn

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        last_login DATE,
        role TEXT
    )
    """)

    conn.commit()
    conn.close()
