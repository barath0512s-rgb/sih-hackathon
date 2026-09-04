import sqlite3
import time
import os

DB_FILE = "vaanisetu_feedback.db"

def init_db():
    """Initialize the SQLite database for storing translations and feedback."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hindi_text TEXT,
            santali_text TEXT,
            is_correct BOOLEAN,
            corrected_text TEXT,
            timestamp REAL
        )
    ''')
    conn.commit()
    conn.close()
    print(f"Database initialized: {DB_FILE}")

def save_feedback(hindi, santali, is_correct, corrected=""):
    """Save user feedback to the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO feedback (hindi_text, santali_text, is_correct, corrected_text, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (hindi, santali, is_correct, corrected, time.time()))
    conn.commit()
    conn.close()

def get_correction(hindi):
    """
    Check if a human has previously corrected or verified this Hindi text.
    Returns the Santali text if found, else None.
    """
    if not os.path.exists(DB_FILE):
        return None
        
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Get the most recent feedback for this hindi phrase
    c.execute('''
        SELECT corrected_text, santali_text, is_correct 
        FROM feedback 
        WHERE hindi_text=? 
        ORDER BY timestamp DESC LIMIT 1
    ''', (hindi,))
    row = c.fetchone()
    conn.close()
    
    if row:
        corrected_text, santali_text, is_correct = row
        # If human provided a correction, use it
        if corrected_text and corrected_text.strip():
            return corrected_text.strip()
        # If human marked it as correct, use the original model output
        if is_correct:
            return santali_text.strip()
            
    return None

def export_to_csv(output_path="training_data/human_feedback_dataset.csv"):
    """Export the database to a CSV for LoRA fine-tuning."""
    import pandas as pd
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM feedback", conn)
    conn.close()
    df.to_csv(output_path, index=False, encoding="utf-8")
    return output_path

if __name__ == "__main__":
    init_db()
