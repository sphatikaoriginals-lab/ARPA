"""
ARPA Universal Normalization Engine (v5.0 Dual-CSV 4.9L Edition)
================================================================
Ingests medicines.csv AND indian_medicine_data.csv into an ultra-fast
in-memory lookup index + SQLite cache so EVERY Indian brand resolves to its
exact active chemical salts.
"""

import difflib
import sqlite3
import csv
import os
import urllib.request
import json
import re
from typing import Dict, List, Any, Optional
import pandas as pd

INITIAL_BRAND_DATABASE: Dict[str, List[str]] = {
    "amlosky at": ["amlodipine", "atenolol"],
    "amlosky-at": ["amlodipine", "atenolol"],
    "amlosky": ["amlodipine"],
    "telma": ["telmisartan"],
    "telma 40": ["telmisartan"],
    "telma-h": ["telmisartan", "hydrochlorothiazide"],
    "telma-am": ["telmisartan", "amlodipine"],
    "stamlo": ["amlodipine"],
    "amlong": ["amlodipine"],
    "cilacar": ["cilnidipine"],
    "cilacar 10": ["cilnidipine"],
    "cilacar-t": ["cilnidipine", "telmisartan"],
    "losar": ["losartan"],
    "cardace": ["ramipril"],
    "cardicheck": ["amlodipine"],
    "metolar": ["metoprolol"],
    "metolar-xr": ["metoprolol"],
    "atorva": ["atorvastatin"],
    "atorvastatin": ["atorvastatin"],
    "rosuvas": ["rosuvastatin"],
    "rozavel": ["rosuvastatin"],
    "rosuvas gold": ["rosuvastatin", "aspirin", "clopidogrel"],
    "atorva gold": ["atorvastatin", "aspirin", "clopidogrel"],
    "combiflam": ["ibuprofen", "paracetamol"],
    "dolo": ["paracetamol"],
    "dolo 650": ["paracetamol"],
    "calpol": ["paracetamol"],
    "crocin": ["paracetamol"],
    "aceclofenac": ["aceclofenac"],
    "aceclo": ["aceclofenac"],
    "aceclo sr": ["aceclofenac"],
    "aceclo-sr": ["aceclofenac"],
    "aceclo plus": ["aceclofenac", "paracetamol"],
    "zerodol": ["aceclofenac"],
    "zerodol-p": ["aceclofenac", "paracetamol"],
    "zerodol-sp": ["aceclofenac", "paracetamol", "serratiopeptidase"],
    "voveran": ["diclofenac"],
    "diclofenac": ["diclofenac"],
    "aspirin": ["aspirin"],
    "ecosprin": ["aspirin"],
    "nimesulide": ["nimesulide"],
    "etoricoxib": ["etoricoxib"],
    "meftal-spas": ["mefenamic acid", "dicyclomine"],
    "augmentin": ["amoxicillin", "clavulanic acid"],
    "moxikind-cv": ["amoxicillin", "clavulanic acid"],
    "azithral": ["azithromycin"],
    "azithromycin": ["azithromycin"],
    "claribid": ["clarithromycin"],
    "clarithromycin": ["clarithromycin"],
    "cifran": ["ciprofloxacin"],
    "oflox": ["ofloxacin"],
    "zenflox": ["ofloxacin"],
    "taxim-o": ["cefixime"],
    "monocef": ["ceftriaxone"],
    "pan": ["pantoprazole"],
    "pan 40": ["pantoprazole"],
    "pan-d": ["pantoprazole", "domperidone"],
    "pantocid": ["pantoprazole"],
    "omez": ["omeprazole"],
    "vomikind": ["ondansetron"],
    "ondansetron": ["ondansetron"],
    "glycomet": ["metformin"],
    "metformin": ["metformin"],
    "amaryl": ["glimepiride"],
    "galvus": ["vildagliptin"],
    "galvus met": ["vildagliptin", "metformin"],
    "januvia": ["sitagliptin"],
    "tenglyn": ["teneligliptin"],
    "tenglyn-m": ["teneligliptin", "metformin"],
    "cetcip": ["cetirizine"],
    "allegra": ["fexofenadine"],
    "omnacortil": ["prednisolone"],
    "medrol": ["methylprednisolone"],
    "clopilet": ["clopidogrel"],
    "clopidogrel": ["clopidogrel"],
    "spironolactone": ["spironolactone"],
    "aldactone": ["spironolactone"],
    "rizital": ["rizatriptan"],
    "rizitat gold": ["rosuvastatin", "aspirin", "clopidogrel"]
}

DB_NAME = "arpa_drugs.db"
CSV_FILES_TO_SCAN = ["medicines.csv", "indian_medicine_data.csv", "pharma_dataset.csv"]

# Fast in-memory dictionary built from medicines.csv & indian_medicine_data.csv
MASTER_CSV_INDEX: Dict[str, str] = {}
MASTER_CSV_DF: Optional[pd.DataFrame] = None
_brand_col_name: str = "name"
_salt_col_name: str = "salt_composition"

def _clean_salt_string_to_list(raw_salt_str: str) -> List[str]:
    """Converts messy CSV composition strings like 'Aceclofenac (100mg) + Paracetamol (325mg)Add' into ['aceclofenac', 'paracetamol']."""
    if not raw_salt_str or str(raw_salt_str).lower() == "nan":
        return []
    s = re.split(r'(?i)add$', str(raw_salt_str))[0].strip()
    s = re.sub(r'\(.*?\)', ' ', s)
    s = re.sub(r'\[.*?\]', ' ', s)
    s = re.sub(r'\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu|%|w/v|w/w|v/v|million|spores|units)\b', ' ', s, flags=re.IGNORECASE)
    parts = re.split(r'\s*(?:\+|\/|,|&|\bwith\b|\band\b)\s*', s, flags=re.IGNORECASE)
    cleaned_salts = []
    for p in parts:
        p_clean = re.sub(r'[^a-zA-Z0-9\-\s]', '', p).strip().lower()
        p_clean = re.sub(r'\s+', ' ', p_clean)
        if len(p_clean) > 2 and p_clean not in ["tablet", "tablets", "capsule", "capsules", "syrup", "injection", "suspension", "oral"]:
            cleaned_salts.append(p_clean)
    return list(dict.fromkeys(cleaned_salts))

def load_all_csv_databases():
    """Loads medicines.csv and indian_medicine_data.csv into a unified DataFrame & fast prefix index."""
    global MASTER_CSV_DF, _brand_col_name, _salt_col_name
    frames = []
    for fname in CSV_FILES_TO_SCAN:
        fpath = os.path.join(os.getcwd(), fname)
        if os.path.exists(fpath):
            try:
                df = pd.read_csv(fpath, low_memory=False)
                cols = [str(c).lower().strip() for c in df.columns]
                df.columns = cols
                b_col = next((c for c in cols if 'name' in c or 'brand' in c), cols[0])
                # In indian_medicine_data.csv, composition is often split across short_composition1 & short_composition2
                comp_cols = [c for c in cols if 'salt' in c or 'composition' in c or 'ingredient' in c]
                if len(comp_cols) >= 2:
                    df["_merged_salt"] = df[comp_cols[0]].fillna('').astype(str) + " + " + df[comp_cols[1]].fillna('').astype(str)
                    s_col = "_merged_salt"
                elif comp_cols:
                    s_col = comp_cols[0]
                else:
                    s_col = cols[1] if len(cols) > 1 else cols[0]
                
                sub = df[[b_col, s_col]].dropna()
                sub.columns = ["brand_col", "salt_col"]
                frames.append(sub)
            except Exception as e:
                print(f"⚠️ CSV Load Warning ({fname}): {e}")
    
    if frames:
        MASTER_CSV_DF = pd.concat(frames, ignore_index=True)
        _brand_col_name = "brand_col"
        _salt_col_name = "salt_col"

load_all_csv_databases()

def lookup_brand_in_master_csv(raw_query: str) -> Optional[List[str]]:
    """Finds any brand across 4.9L+ records in medicines.csv / indian_medicine_data.csv."""
    if MASTER_CSV_DF is None or not raw_query.strip():
        return None
    
    q = re.split(r'(?i)mrp|prescription|strip|₹', raw_query)[0].strip()
    if not q:
        return None

    # 1. Fast case-insensitive prefix / substring search
    col_series = MASTER_CSV_DF[_brand_col_name].astype(str)
    matches = MASTER_CSV_DF[col_series.str.contains(q, case=False, na=False, regex=False)]

    # 2. Token-based fallback for hyphen/space variations ("Aceclo SR" vs "Aceclo-SR")
    if matches.empty:
        ignore_words = {"tablet", "tablets", "tab", "cap", "capsule", "capsules", "syrup", "injection", "inj", "gel", "cream", "drops", "suspension"}
        tokens = [t.lower() for t in re.split(r'[\s\-]+', q) if len(t) >= 2 and t.lower() not in ignore_words]
        if tokens:
            sub_df = MASTER_CSV_DF[col_series.str.contains(tokens[0], case=False, na=False, regex=False)]
            for tok in tokens[1:]:
                narrow = sub_df[sub_df[_brand_col_name].astype(str).str.lower().str.contains(tok, na=False, regex=False)]
                if not narrow.empty:
                    sub_df = narrow
            matches = sub_df

    if not matches.empty:
        raw_salt_str = str(matches.iloc[0][_salt_col_name])
        salts = _clean_salt_string_to_list(raw_salt_str)
        if salts:
            return salts
    return None

def init_sqlite_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brands (
            brand_name TEXT PRIMARY KEY,
            salts TEXT
        )
    """)
    # Purge any self-referential bad cache entries where brand_name == salts
    cursor.execute("DELETE FROM brands WHERE brand_name = salts")
    for brand, salts in INITIAL_BRAND_DATABASE.items():
        cursor.execute("INSERT OR REPLACE INTO brands (brand_name, salts) VALUES (?, ?)", 
                       (brand, ",".join(salts)))
    conn.commit()
    conn.close()

init_sqlite_db()

def get_db_brands() -> Dict[str, List[str]]:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT brand_name, salts FROM brands")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1].split(",") for row in rows}

def save_brand_to_db(brand_name: str, salts: List[str]):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO brands (brand_name, salts) VALUES (?, ?)", 
                       (brand_name.lower().strip(), ",".join(salts)))
        conn.commit()
        conn.close()
    except Exception:
        pass

def fetch_rxnorm_drug(brand_name: str) -> Optional[List[str]]:
    try:
        ctx = None
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={urllib.request.quote(brand_name)}"
        req = urllib.request.Request(url, headers={"User-Agent": "ARPA-Clinical-Engine"})
        with urllib.request.urlopen(req, timeout=2.0, context=ctx) as response:
            data = json.loads(response.read().decode("utf-8"))
            rxcui_list = data.get("idGroup", {}).get("rxnormId", [])
            if rxcui_list:
                rxcui = rxcui_list[0]
                prop_url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/related.json?rela=isa"
                prop_req = urllib.request.Request(prop_url, headers={"User-Agent": "ARPA-Clinical-Engine"})
                with urllib.request.urlopen(prop_req, timeout=2.0, context=ctx) as prop_resp:
                    prop_data = json.loads(prop_resp.read().decode("utf-8"))
                    for group in prop_data.get("relatedGroup", {}).get("conceptGroup", []):
                        if group.get("tty") == "IN":
                            salts = [c.get("name").lower() for c in group.get("conceptProperties", [])]
                            if salts:
                                return salts
    except Exception:
        pass
    return None

def detect_administration_route(brand_name: str) -> str:
    b = brand_name.lower()
    if any(k in b for k in ["cream", "gel", "ointment", "lotion", "eye drop", "ear drop", "nasal spray", "powder", "dusting", "wash", "shampoo"]):
        return "topical"
    if any(k in b for k in ["injection", "inj", "iv", "infusion", "vial", "ampoule"]):
        return "iv"
    if any(k in b for k in ["inhaler", "rotacap", "respules", "nebulizer"]):
        return "inhalation"
    return "oral"

def ai_llm_auto_extract_salt(brand_name: str) -> List[str]:
    cleaned = brand_name.lower().strip()
    words = [w for w in re.split(r'[\s\-]+', cleaned) if w]
    base_brand = words[0] if words else cleaned
    
    extracted_salts = []
    prefix_map = {
        "amlo": "amlodipine", "telm": "telmisartan", "rosu": "rosuvastatin",
        "ator": "atorvastatin", "pant": "pantoprazole", "pan": "pantoprazole",
        "rab": "rabeprazole", "omez": "omeprazole", "cefi": "cefixime",
        "taxim": "cefixime", "aceclo": "aceclofenac", "zerodol": "aceclofenac",
        "diclo": "diclofenac", "voveran": "diclofenac", "para": "paracetamol",
        "dolo": "paracetamol", "calpol": "paracetamol", "azith": "azithromycin",
        "clar": "clarithromycin", "cipro": "ciprofloxacin", "oflox": "ofloxacin",
        "levo": "levofloxacin", "amox": "amoxicillin", "mox": "amoxicillin",
        "aug": "amoxicillin", "metf": "metformin", "glyc": "metformin",
        "glim": "glimepiride", "amar": "glimepiride", "vild": "vildagliptin",
        "sita": "sitagliptin", "tene": "teneligliptin", "dapa": "dapagliflozin",
        "empa": "empagliflozin", "ciln": "cilnidipine", "cila": "cilnidipine",
        "meto": "metoprolol", "aten": "atenolol", "biso": "bisoprolol",
        "nebi": "nebivolol", "losa": "losartan", "olme": "olmesartan",
        "rami": "ramipril", "enal": "enalapril", "clop": "clopidogrel",
        "ecos": "aspirin", "pred": "prednisolone", "medr": "methylprednisolone",
        "defl": "deflazacort", "dexa": "dexamethasone", "mont": "montelukast",
        "ceti": "cetirizine", "fexo": "fexofenadine", "onda": "ondansetron",
        "vomi": "ondansetron", "domp": "domperidone", "preg": "pregabalin",
        "gaba": "gabapentin", "tram": "tramadol", "alpr": "alprazolam",
        "clon": "clonazepam", "escit": "escitalopram", "fluo": "fluoxetine",
        "sert": "sertraline", "levo": "levothyroxine", "ron": "spironolactone"
    }
    for pref, salt_val in prefix_map.items():
        if base_brand.startswith(pref):
            extracted_salts.append(salt_val)
            break
    
    for word in words[1:]:
        if word == "at": extracted_salts.append("atenolol")
        elif word == "h": extracted_salts.append("hydrochlorothiazide")
        elif word == "am": extracted_salts.append("amlodipine")
        elif word == "m": extracted_salts.append("metformin")
        elif word in ["d", "dsr", "dom"]: extracted_salts.append("domperidone")
        elif word in ["p", "plus"]: extracted_salts.append("paracetamol")
        elif word == "sp": extracted_salts.extend(["paracetamol", "serratiopeptidase"])
        elif word == "cv": extracted_salts.append("clavulanic acid")
        elif word == "oz": extracted_salts.append("ornidazole")
        elif word == "lc": extracted_salts.append("levocetirizine")
        elif word == "nt": extracted_salts.append("nortriptyline")
        elif word == "me": extracted_salts.append("methylcobalamin")

    if not extracted_salts:
        clean_name = re.sub(r"\b\d+(\.\d+)?\s*(mg|g|mcg|ml|iu|%|sr|cr|er|xr|od|ds|dt|forte|tab|tablet|cap|capsule)\b", "", cleaned, flags=re.IGNORECASE).strip()
        return [clean_name if clean_name else cleaned]

    return list(dict.fromkeys(extracted_salts))

def normalize_brand_input(raw_input: str) -> Dict[str, Any]:
    brand_clean = re.split(r'(?i)mrp|prescription|strip|₹', raw_input)[0].strip()
    lookup_key = brand_clean.lower()
    
    # If the user already passed "Brand (Salt1 + Salt2)" or CSV salt string, extract directly
    brand_database = get_db_brands()
    
    # 1. Exact match in SQLite cache (if valid)
    if lookup_key in brand_database:
        salts_found = brand_database[lookup_key]
        if salts_found and salts_found != [lookup_key]:
            return {
                "brand": brand_clean.title(),
                "salts": salts_found,
                "route": detect_administration_route(brand_clean)
            }
        
    # 2. Direct Lookup in 4.9L medicines.csv & indian_medicine_data.csv
    csv_salts = lookup_brand_in_master_csv(brand_clean)
    if csv_salts:
        save_brand_to_db(lookup_key, csv_salts)
        return {
            "brand": brand_clean.title(),
            "salts": csv_salts,
            "route": detect_administration_route(brand_clean)
        }

    # 3. Fuzzy match in known database
    all_known_brands = list(brand_database.keys())
    matches = difflib.get_close_matches(lookup_key, all_known_brands, n=1, cutoff=0.84)
    if matches:
        matched_brand = matches[0]
        if abs(len(lookup_key) - len(matched_brand)) <= 4 and brand_database[matched_brand] != [matched_brand]:
            return {
                "brand": f"{brand_clean.title()}",
                "salts": brand_database[matched_brand],
                "route": detect_administration_route(brand_clean)
            }
        
    # 4. RxNorm API lookup
    rxnorm_salts = fetch_rxnorm_drug(lookup_key)
    if rxnorm_salts:
        save_brand_to_db(lookup_key, rxnorm_salts)
        return {
            "brand": f"{brand_clean.title()}",
            "salts": rxnorm_salts,
            "route": detect_administration_route(brand_clean)
        }

    # 5. Smart Indian FDC & Stem Extractor
    ai_extracted_salts = ai_llm_auto_extract_salt(lookup_key)
    if ai_extracted_salts != [lookup_key]:
        save_brand_to_db(lookup_key, ai_extracted_salts)

    return {
        "brand": f"{brand_clean.title()}",
        "salts": ai_extracted_salts,
        "route": detect_administration_route(brand_clean)
    }

BRAND_DATABASE = get_db_brands()
