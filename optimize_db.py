import sqlite3
import time

DB_PATH = "drug_cache.db"

def optimize_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("[*] Checking database structure...")
    
    # Check current table schema
    cursor.execute("PRAGMA table_info(salt_cache)")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"[*] Current columns: {columns}")
    
    # Add index on brand_name if not already present
    print("[*] Creating B-Tree Index on brand_name (COLLATE NOCASE)...")
    start = time.time()
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_brand_name ON salt_cache(brand_name COLLATE NOCASE)")
    
    # Run PRAGMA optimize & VACUUM to defragment the SQLite file
    print("[*] Optimizing database pages...")
    cursor.execute("PRAGMA optimize")
    conn.commit()
    conn.close()
    
    duration = (time.time() - start) * 1000
    print(f"[*] Optimization complete in {duration:.2f} ms.")

if __name__ == "__main__":
    optimize_database()