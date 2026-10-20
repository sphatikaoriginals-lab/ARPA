import sqlite3
from datetime import datetime

DB_FILE = "feedback_memory.db"

def init_feedback_db():
    """Doctor decisions log karne ke liye SQLite DB initialize karta hai."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctor_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salt_1 TEXT,
            salt_2 TEXT,
            doctor_id TEXT,
            action TEXT,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def log_doctor_feedback(salt_1: str, salt_2: str, doctor_id: str, action: str, reason: str = "Clinical judgment") -> dict:
    """Doctor ke alert decision (CONFIRMED ya DISMISSED) ko store karta hai."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO doctor_feedback (salt_1, salt_2, doctor_id, action, reason)
        VALUES (?, ?, ?, ?, ?)
    """, (salt_1.lower().strip(), salt_2.lower().strip(), doctor_id, action.upper(), reason))
    conn.commit()

    # Consensus analytics calculate karein
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN action = 'CONFIRMED' THEN 1 ELSE 0 END) as confirmed,
            SUM(CASE WHEN action = 'DISMISSED' THEN 1 ELSE 0 END) as dismissed
        FROM doctor_feedback
        WHERE (salt_1 = ? AND salt_2 = ?) OR (salt_1 = ? AND salt_2 = ?)
    """, (salt_1.lower(), salt_2.lower(), salt_2.lower(), salt_1.lower()))
    
    row = cursor.fetchone()
    conn.close()

    total = row[0] or 0
    confirmed = row[1] or 0
    dismissed = row[2] or 0

    status = "Active Rule"
    if total >= 3 and (dismissed / total) >= 0.7:
        status = "Suppressed via Clinical Consensus"

    return {
        "total_reviews": total,
        "confirmed": confirmed,
        "dismissed": dismissed,
        "system_status": status
    }

def is_rule_suppressed(salt_1: str, salt_2: str) -> bool:
    """Check karta hai ki kya doctors ne is rule ko suppress kiya hua hai."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN action = 'DISMISSED' THEN 1 ELSE 0 END) as dismissed
            FROM doctor_feedback
            WHERE (salt_1 = ? AND salt_2 = ?) OR (salt_1 = ? AND salt_2 = ?)
        """, (salt_1.lower().strip(), salt_2.lower().strip(), salt_2.lower().strip(), salt_1.lower().strip()))
        
        row = cursor.fetchone()
        conn.close()

        if row and row[0] and row[0] >= 3:
            total = row[0]
            dismissed = row[1] or 0
            if (dismissed / total) >= 0.7:
                return True
        return False
    except Exception:
        return False