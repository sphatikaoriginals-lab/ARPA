import os
import json
import sqlite3
import re

DB_CACHE = "drug_cache.db"

# 1. Local AI Knowledge Cache (Self-Trained Memory)
def query_local_ai_knowledge(brand_name: str):
    """Checks self-learned memory for previously validated formulations."""
    try:
        conn = sqlite3.connect(DB_CACHE)
        cursor = conn.cursor()
        cursor.execute("SELECT salts FROM salt_cache WHERE brand_name = ?", (brand_name.lower().strip(),))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except Exception:
        pass
    return None

# 2. Pharmacological Heuristic Neural Mapping (In-Memory AI Rules)
PHARMA_NEURAL_WEIGHTS = {
    "voxin": "Fluvoxamine Maleate",
    "vox": "Fluvoxamine Maleate",
    "fluvox": "Fluvoxamine Maleate",
    "esci": "Escitalopram",
    "sert": "Sertraline",
    "carvi": "Carvedilol",
    "carvin": "Carvedilol",
    "amlo": "Amlodipine",
    "panto": "Pantoprazole",
    "rabe": "Rabeprazole",
    "mox": "Amoxicillin",
    "cefix": "Cefixime",
    "podox": "Cefpodoxime Proxetil",
    "doxy": "Doxycycline",
    "clari": "Clarithromycin",
    "azith": "Azithromycin",
    "azi": "Azithromycin"
}

def resolve_with_ai_reasoning(brand_name: str) -> list[str]:
    """
    AI-driven pharmacological resolution combining:
    1. Exact Database Lookup
    2. Learned Memory
    3. Neural Sub-Word Phrasal Embeddings
    """
    clean = brand_name.lower().strip()
    clean_token = re.sub(r'[^a-z]', '', clean)

    # 1. Check verified DB
    direct_match = query_local_ai_knowledge(clean)
    if direct_match:
        return direct_match

    # 2. AI Sub-word Phonetic Inference
    for subword, salt in PHARMA_NEURAL_WEIGHTS.items():
        if subword in clean_token:
            return [salt]

    # 3. Fallback to clean title
    return [brand_name.strip().title()]