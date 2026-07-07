import sqlite3
import pandas as pd
from datetime import datetime
import os

# Default database name - when Dockerized, this should be mapped to a persistent volume
DB_NAME = "tracker.db"

def init_db(db_path: str = DB_NAME) -> None:
    """
    Initializes the SQLite database. 
    Creates the 'applications' table if it does not already exist.
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                role_title TEXT NOT NULL,
                location TEXT,
                job_type TEXT,
                platform TEXT,
                job_url TEXT,
                posting_path TEXT,
                resume_path TEXT,
                cover_letter TEXT,
                contact_recruiter TEXT,
                status TEXT,
                priority TEXT,
                salary_range TEXT,
                key_requirements TEXT,
                notes TEXT,
                date_applied TEXT,
                last_updated TEXT
            )
        """)
        conn.commit()

def insert_application(data: dict, db_path: str = DB_NAME) -> int:
    """
    Inserts a new job application record into the database.
    Expects a dictionary containing all the keys mapped from the UI.
    Returns the ID of the newly inserted row.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO applications (
                company, role_title, location, job_type, platform, 
                job_url, posting_path, resume_path, cover_letter, 
                contact_recruiter, status, priority, salary_range, 
                key_requirements, notes, date_applied, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('company', ''),
            data.get('role_title', ''),
            data.get('location', ''),
            data.get('job_type', ''),
            data.get('platform', ''),
            data.get('job_url', ''),
            data.get('posting_path', ''),
            data.get('resume_path', ''),
            data.get('cover_letter', 'No'),
            data.get('contact_recruiter', ''),
            data.get('status', 'Applied'),
            data.get('priority', 'Medium'),
            data.get('salary_range', 'n/a'),
            data.get('key_requirements', ''),
            data.get('notes', ''),
            now_str, # date_applied
            now_str  # last_updated
        ))
        conn.commit()
        return cursor.lastrowid

def get_all_applications(db_path: str = DB_NAME) -> pd.DataFrame:
    """
    Retrieves all applications from the database and returns them as a Pandas DataFrame.
    This is formatted specifically for Streamlit's st.data_editor.
    """
    # If the DB doesn't exist yet, return an empty DataFrame with correct columns
    if not os.path.exists(db_path):
        init_db(db_path)
        
    with sqlite3.connect(db_path) as conn:
        # Read straight into Pandas for easy UI rendering
        df = pd.read_sql_query("SELECT * FROM applications ORDER BY id DESC", conn)
        return df

def update_application(app_id: int, updates: dict, db_path: str = DB_NAME) -> None:
    """
    Updates an existing application record.
    `updates` should be a dictionary of {column_name: new_value}.
    Automatically updates the `last_updated` timestamp.
    """
    if not updates:
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updates['last_updated'] = now_str

    # Dynamically build the SET clause based on the passed dictionary
    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
    values = list(updates.values())
    values.append(app_id) # For the WHERE clause

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE applications 
            SET {set_clause} 
            WHERE id = ?
        """, tuple(values))
        conn.commit()

def delete_application(app_id: int, db_path: str = DB_NAME) -> None:
    """
    Deletes an application record by ID.
    """
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM applications WHERE id = ?", (app_id,))
        conn.commit()