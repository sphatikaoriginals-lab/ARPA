import csv
import json
import os
import re
import sqlite3
import urllib.request

DB_FILE = "drug_cache.db"
# 50,000+ Indian pharmaceutical brands dataset
DATASET_CSV_URL = "https://raw.githubusercontent.com/junioralive/Indian-Medicine-Dataset/main/DATA/indian_medicine_data.csv"
LOCAL_CSV_BACKUP = "indian_medicine_data.csv"

def clean_brand_name(name: str) -> str:
    """Removes dosage forms, strengths, and packaging noise."""
    cleaned = name.lower()
    cleaned = re.sub(
        r"\b(tablet|tablets|capsule|capsules|syrup|injection|drops|gel|ointment|cream|suspension|infusion|solution|oral)\b",
        "",
        cleaned,
    )
    cleaned = re.sub(
        r"\b(strip of \d+|bottle of \d+|pack of \d+|tube of \d+)\b",
        "",
        cleaned,
    )
    cleaned = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|ml|g|iu|%|k)?\b", "", cleaned)
    cleaned = re.sub(
        r"\b(sr|cr|dt|dsr|forte|plus|sp|tab|cap|syp|inj|duo|av|am|h|ls|gp|lc|p|d|aq)\b",
        "",
        cleaned,
    )
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", cleaned).strip()
    return " ".join(cleaned.split())

def clean_salt_name(salt_str: str) -> str:
    """Extracts chemical salt name by stripping dosage strengths."""
    if not salt_str:
        return ""
    cleaned = re.sub(r"\([^)]*\)", "", salt_str)
    cleaned = re.sub(
        r"\b\d+(\.\d+)?\s*(mg|mcg|ml|g|iu|%|w/v|w/w)?\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\b(ip|bp|usp)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^a-zA-Z\s\-]", " ", cleaned).strip()
    return " ".join(cleaned.split()).title()

def download_and_import():
    print("=" * 70)
    print("ARPA Mega-Scale Ingestion: 50,000+ Indian Pharmaceutical Dataset")
    print("=" * 70)

    # 1. Download dataset CSV if not locally present
    if not os.path.exists(LOCAL_CSV_BACKUP):
        print("[*] Downloading dataset from repository...")
        try:
            urllib.request.urlretrieve(DATASET_CSV_URL, LOCAL_CSV_BACKUP)
            print(f"[+] Download complete! Saved as '{LOCAL_CSV_BACKUP}'.")
        except Exception as e:
            print(f"[-] Download failed: {e}")
            return
    else:
        print(f"[+] Using existing local file: '{LOCAL_CSV_BACKUP}'")

    # 2. Setup SQLite Table
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS salt_cache (
            brand_name TEXT PRIMARY KEY,
            salts TEXT
        )
    """)
    conn.commit()

    # 3. Stream & Process CSV
    print("[*] Parsing and importing medicines into drug_cache.db...")
    imported_count = 0
    batch_records = []

    with open(LOCAL_CSV_BACKUP, mode="r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)

        for row in reader:
            raw_name = row.get("name", "")
            if not raw_name:
                continue

            salts = []
            for col in ["short_composition1", "short_composition2", "composition"]:
                val = row.get(col, "")
                if val:
                    parts = re.split(r"[+/]", val)
                    for p in parts:
                        s_clean = clean_salt_name(p)
                        if s_clean and len(s_clean) > 2 and s_clean not in salts:
                            salts.append(s_clean)

            if not salts:
                continue

            salts_json = json.dumps(salts)
            raw_lower = raw_name.lower().strip()
            cleaned_brand = clean_brand_name(raw_name)

            # Store variations for fast lookup
            batch_records.append((raw_lower, salts_json))
            if cleaned_brand and cleaned_brand != raw_lower:
                batch_records.append((cleaned_brand, salts_json))

            first_token = cleaned_brand.split()[0] if cleaned_brand else raw_lower.split()[0]
            if len(first_token) >= 3:
                batch_records.append((first_token, salts_json))

            imported_count += 1

            if len(batch_records) >= 5000:
                cursor.executemany(
                    "INSERT OR REPLACE INTO salt_cache (brand_name, salts) VALUES (?, ?)",
                    batch_records,
                )
                conn.commit()
                batch_records.clear()
                print(f" -> Ingested {imported_count} medicines...")

    if batch_records:
        cursor.executemany(
            "INSERT OR REPLACE INTO salt_cache (brand_name, salts) VALUES (?, ?)",
            batch_records,
        )
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM salt_cache")
    total_keys = cursor.fetchone()[0]
    conn.close()

    print("=" * 70)
    print(f"✓ SUCCESSFULLY IMPORTED: {imported_count} Formulations")
    print(f"★ TOTAL SEARCH KEYS IN 'drug_cache.db': {total_keys}")
    print("=" * 70)

if __name__ == "__main__":
    download_and_import()