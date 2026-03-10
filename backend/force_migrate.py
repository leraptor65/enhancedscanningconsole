import sqlite3
import os

db_path = "/app/backend/data/scans.db"
# db_path = "./data/scans.db"  # Try absolute path from inside container 

try:
    print(f"Connecting to {db_path}...")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Check current columns
    cur.execute("PRAGMA table_info(scans)")
    cols = [row[1] for row in cur.fetchall()]
    print("Current columns:", cols)
    
    if "count" not in cols:
        print("Adding count column...")
        cur.execute("ALTER TABLE scans ADD COLUMN count INTEGER DEFAULT 1")
        conn.commit()
        print("Column added successfully.")
    else:
        print("Column already exists.")
        
    conn.close()
except Exception as e:
    print("Error:", e)
