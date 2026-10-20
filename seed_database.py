import sqlite3
import json

DB_FILE = "drug_cache.db"

# Masters in Medicine (MD General Medicine) Comprehensive Pharmacology Ingestion
MD_CURRICULUM_DRUG_DATA = {
    # =========================================================================
    # 1. CARDIOVASCULAR SYSTEM & HEMATOLOGY
    # =========================================================================
    # Antiplatelets & Anticoagulants
    "ecosprin": ["Aspirin"],
    "ecosprin 75": ["Aspirin"],
    "ecosprin 150": ["Aspirin"],
    "ecosprin av": ["Aspirin", "Atorvastatin"],
    "clopilet": ["Clopidogrel"],
    "clopilet 75": ["Clopidogrel"],
    "clopilet a": ["Clopidogrel", "Aspirin"],
    "deplatt": ["Clopidogrel"],
    "deplatt a": ["Clopidogrel", "Aspirin"],
    "brilinta": ["Ticagrelor"],
    "clexane": ["Enoxaparin"],
    "lonopin": ["Enoxaparin"],
    "warf": ["Warfarin"],
    "pradaxa": ["Dabigatran"],
    "xarelto": ["Rivaroxaban"],
    "eliquis": ["Apixaban"],

    # Antihypertensives (RAAS Inhibitors)
    "telma": ["Telmisartan"],
    "telma 40": ["Telmisartan"],
    "telma 80": ["Telmisartan"],
    "telmikind": ["Telmisartan"],
    "telma h": ["Telmisartan", "Hydrochlorothiazide"],
    "telma am": ["Telmisartan", "Amlodipine"],
    "repace": ["Losartan"],
    "repace h": ["Losartan", "Hydrochlorothiazide"],
    "olmy": ["Olmesartan"],
    "cardace": ["Ramipril"],
    "cardace 2.5": ["Ramipril"],
    "cardace 5": ["Ramipril"],
    "cardace h": ["Ramipril", "Hydrochlorothiazide"],
    "envas": ["Enalapril"],

    # Calcium Channel Blockers (CCBs)
    "stamlo": ["Amlodipine"],
    "stamlo 5": ["Amlodipine"],
    "amlong": ["Amlodipine"],
    "amlong 5": ["Amlodipine"],
    "amlosky": ["Amlodipine"],
    "amlosky at": ["Amlodipine", "Atenolol"],
    "amlosafe": ["Amlodipine"],
    "amlosafe at": ["Amlodipine", "Atenolol"],
    "cilacar": ["Cilnidipine"],
    "cilacar 10": ["Cilnidipine"],
    "cilacar 20": ["Cilnidipine"],
    "cilacar t": ["Cilnidipine", "Telmisartan"],
    "calaptin": ["Verapamil"],
    "dilzem": ["Diltiazem"],
    "nifecard": ["Nifedipine"],

    # Beta Blockers
    "betaloc": ["Metoprolol"],
    "betaloc 25": ["Metoprolol"],
    "betaloc 50": ["Metoprolol"],
    "metolar": ["Metoprolol"],
    "concor": ["Bisoprolol"],
    "concor 5": ["Bisoprolol"],
    "aten": ["Atenolol"],
    "aten 50": ["Atenolol"],
    "aten d": ["Atenolol", "Chlorthalidone"],
    "carca": ["Carvedilol"],
    "labebet": ["Labetalol"],
    "nebicip": ["Nebivolol"],

    # Diuretics
    "lasix": ["Furosemide"],
    "dytor": ["Torsemide"],
    "dytor 10": ["Torsemide"],
    "dytor 20": ["Torsemide"],
    "dytor plus": ["Torsemide", "Spironolactone"],
    "aldactone": ["Spironolactone"],
    "aldactone 25": ["Spironolactone"],
    "aldactone 50": ["Spironolactone"],

    # Lipid-Lowering Statins
    "atorva": ["Atorvastatin"],
    "atorva 10": ["Atorvastatin"],
    "atorva 20": ["Atorvastatin"],
    "atorva 40": ["Atorvastatin"],
    "storvas": ["Atorvastatin"],
    "rosuvas": ["Rosuvastatin"],
    "rosuvas 10": ["Rosuvastatin"],
    "rozavel": ["Rosuvastatin"],
    "lipaglyn": ["Saroglitazar"],

    # Antiarrhythmics & Emergency Cardio
    "cordarone": ["Amiodarone"],
    "lanoxin": ["Digoxin"],

    # =========================================================================
    # 2. ENDOCRINOLOGY & METABOLISM
    # =========================================================================
    "glycomet": ["Metformin"],
    "glycomet 500": ["Metformin"],
    "glycomet 850": ["Metformin"],
    "glycomet 1000": ["Metformin"],
    "glycomet gp": ["Metformin", "Glimepiride"],
    "glycomet gp 1": ["Metformin", "Glimepiride"],
    "glycomet gp 2": ["Metformin", "Glimepiride"],
    "amaryl": ["Glimepiride"],
    "amaryl 1": ["Glimepiride"],
    "amaryl 2": ["Glimepiride"],
    "amaryl m": ["Glimepiride", "Metformin"],
    "janumet": ["Metformin", "Sitagliptin"],
    "janumet 50/500": ["Metformin", "Sitagliptin"],
    "januvia": ["Sitagliptin"],
    "galvus": ["Vildagliptin"],
    "galvus met": ["Vildagliptin", "Metformin"],
    "tenelimac": ["Teneligliptin"],
    "trajenta": ["Linagliptin"],
    "forxiga": ["Dapagliflozin"],
    "forxiga 10": ["Dapagliflozin"],
    "oxra": ["Dapagliflozin"],
    "jardiance": ["Empagliflozin"],
    "jardiance 10": ["Empagliflozin"],
    "jardiance 25": ["Empagliflozin"],
    "thyronorm": ["Levothyroxine"],
    "eltroxin": ["Levothyroxine"],
    "neomercazole": ["Carbimazole"],

    # =========================================================================
    # 3. ANTIMICROBIALS & INFECTIOUS DISEASES
    # =========================================================================
    # Beta-Lactams & Cephalosporins
    "augmentin": ["Amoxicillin", "Clavulanic Acid"],
    "augmentin 625": ["Amoxicillin", "Clavulanic Acid"],
    "augmentin 625 duo": ["Amoxicillin", "Clavulanic Acid"],
    "clavam": ["Amoxicillin", "Clavulanic Acid"],
    "clavam 625": ["Amoxicillin", "Clavulanic Acid"],
    "moxikind cv": ["Amoxicillin", "Clavulanic Acid"],
    "mox": ["Amoxicillin"],
    "novamox": ["Amoxicillin"],
    "pipzo": ["Piperacillin", "Tazobactam"],
    "taxim o": ["Cefixime"],
    "taxim": ["Cefotaxime"],
    "cefix": ["Cefixime"],
    "mahacef": ["Cefixime"],
    "ceftas": ["Cefixime"],
    "monocef": ["Ceftriaxone"],
    "monocef 1g": ["Ceftriaxone"],
    "zefi": ["Cefuroxime"],
    "ceftum": ["Cefuroxime"],
    "meronem": ["Meropenem"],

    # Macrolides, Tetracyclines & Fluoroquinolones
    "azikem": ["Azithromycin"],
    "azikem 250": ["Azithromycin"],
    "azikem 500": ["Azithromycin"],
    "azithral": ["Azithromycin"],
    "azithral 500": ["Azithromycin"],
    "zady": ["Azithromycin"],
    "azee": ["Azithromycin"],
    "claribid": ["Clarithromycin"],
    "claribid 500": ["Clarithromycin"],
    "doxykind": ["Doxycycline"],
    "doxicip": ["Doxycycline"],
    "cifran": ["Ciprofloxacin"],
    "ciplox": ["Ciprofloxacin"],
    "oflox": ["Ofloxacin"],
    "zanocin": ["Ofloxacin"],
    "zenflox oz": ["Ofloxacin", "Ornidazole"],
    "norflox tz": ["Norfloxacin", "Tinidazole"],
    "levomac": ["Levofloxacin"],
    "avelox": ["Moxifloxacin"],

    # ICU, Antifungal & Antiprotozoal
    "linospan": ["Linezolid"],
    "vancocin": ["Vancomycin"],
    "flagyl": ["Metronidazole"],
    "forcan": ["Fluconazole"],
    "forcan 150": ["Fluconazole"],
    "v-fend": ["Voriconazole"],

    # =========================================================================
    # 4. GASTROENTEROLOGY & HEPATOLOGY
    # =========================================================================
    "pan": ["Pantoprazole"],
    "pan 40": ["Pantoprazole"],
    "pan d": ["Pantoprazole", "Domperidone"],
    "pantop": ["Pantoprazole"],
    "pantop d": ["Pantoprazole", "Domperidone"],
    "pantocid": ["Pantoprazole"],
    "pantocid d": ["Pantoprazole", "Domperidone"],
    "pantocid dsr": ["Pantoprazole", "Domperidone"],
    "omez": ["Omeprazole"],
    "omez 20": ["Omeprazole"],
    "omez d": ["Omeprazole", "Domperidone"],
    "rabekind": ["Rabeprazole"],
    "rabekind dsr": ["Rabeprazole", "Domperidone"],
    "razo": ["Rabeprazole"],
    "razo d": ["Rabeprazole", "Domperidone"],
    "nexpro": ["Esomeprazole"],
    "nexpro rd": ["Esomeprazole", "Domperidone"],
    "rantac": ["Ranitidine"],
    "aciloc": ["Ranitidine"],
    "vomikind": ["Ondansetron"],
    "emset": ["Ondansetron"],
    "perinorm": ["Metoclopramide"],
    "ganaton": ["Itopride"],
    "duphalac": ["Lactulose"],
    "cremaffin": ["Liquid Paraffin", "Milk of Magnesia"],
    "gelusil": ["Aluminium Hydroxide", "Magnesium Hydroxide", "Dimethicone"],
    "digene": ["Magnesium Hydroxide", "Aluminium Hydroxide", "Simethicone"],
    "rifagut": ["Rifaximin"],
    "rifagut 400": ["Rifaximin"],
    "rifagut 550": ["Rifaximin"],
    "udiliv": ["Ursodeoxycholic Acid"],
    "udiliv 300": ["Ursodeoxycholic Acid"],

    # =========================================================================
    # 5. RESPIRATORY MEDICINE
    # =========================================================================
    "asthalin": ["Salbutamol"],
    "duolin": ["Levosalbutamol", "Ipratropium Bromide"],
    "budecort": ["Budesonide"],
    "foracort": ["Formoterol", "Budesonide"],
    "seroflo": ["Salmeterol", "Fluticasone"],
    "tiova": ["Tiotropium"],
    "montair lc": ["Montelukast", "Levocetirizine"],
    "montek lc": ["Montelukast", "Levocetirizine"],
    "telekast l": ["Montelukast", "Levocetirizine"],
    "allegra": ["Fexofenadine"],
    "allegra 120": ["Fexofenadine"],
    "cetzine": ["Cetirizine"],
    "deriphyllin": ["Theophylline", "Etophylline"],
    "ascoril ls": ["Levosalbutamol", "Ambroxol", "Guaifenesin"],
    "alex": ["Dextromethorphan", "Chlorpheniramine", "Phenylephrine"],

    # =========================================================================
    # 6. NEUROLOGY, PSYCHIATRY & ANALGESICS
    # =========================================================================
    "levipil": ["Levetiracetam"],
    "levipil 500": ["Levetiracetam"],
    "encorate": ["Sodium Valproate"],
    "encorate chrono": ["Sodium Valproate", "Valproic Acid"],
    "eptoin": ["Phenytoin"],
    "tegrital": ["Carbamazepine"],
    "lacosam": ["Lacosamide"],
    "zapiz": ["Clonazepam"],
    "clonafit": ["Clonazepam"],
    "alprax": ["Alprazolam"],
    "ativan": ["Lorazepam"],
    "calmpose": ["Diazepam"],
    "nexito": ["Escitalopram"],
    "nexito plus": ["Escitalopram", "Clonazepam"],
    "gaba": ["Gabapentin"],
    "maxgalin": ["Pregabalin"],
    "dolo": ["Paracetamol"],
    "dolo 650": ["Paracetamol"],
    "calpol": ["Paracetamol"],
    "calpol 500": ["Paracetamol"],
    "calpol 650": ["Paracetamol"],
    "crocin": ["Paracetamol"],
    "pacimol": ["Paracetamol"],
    "combiflam": ["Ibuprofen", "Paracetamol"],
    "brufen": ["Ibuprofen"],
    "voveran": ["Diclofenac"],
    "voveran sr": ["Diclofenac"],
    "volini": ["Diclofenac"],
    "dynapar": ["Diclofenac"],
    "aceclo": ["Aceclofenac"],
    "aceclo sr": ["Aceclofenac"],
    "hifenac": ["Aceclofenac"],
    "hifenac p": ["Aceclofenac", "Paracetamol"],
    "zerodol": ["Aceclofenac"],
    "zerodol p": ["Aceclofenac", "Paracetamol"],
    "zerodol sp": ["Aceclofenac", "Paracetamol", "Serratiopeptidase"],
    "ultracet": ["Tramadol", "Paracetamol"],
    "etoshine": ["Etoricoxib"],
    "arcoxia": ["Etoricoxib"],
    "nise": ["Nimesulide"],
    "chymoral forte": ["Trypsin", "Chymotrypsin"],
    "drotin": ["Drotaverine"],
    "drotin m": ["Drotaverine", "Mefenamic Acid"],
    "meftal spas": ["Mefenamic Acid", "Dicyclomine"],
    "meftal forte": ["Mefenamic Acid", "Paracetamol"],
    "shelcal": ["Calcium", "Vitamin D3"],
    "shelcal 500": ["Calcium", "Vitamin D3"],
    "becosules": ["Vitamin B-Complex", "Vitamin C"],
    "neurobion forte": ["Vitamin B-Complex", "Vitamin B12"],
    "limcee": ["Vitamin C"]
}

def seed_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS salt_cache (
            brand_name TEXT PRIMARY KEY,
            salts TEXT
        )
    """)

    inserted = 0
    for brand, salts in MD_CURRICULUM_DRUG_DATA.items():
        cursor.execute("""
            INSERT OR REPLACE INTO salt_cache (brand_name, salts)
            VALUES (?, ?)
        """, (brand.lower().strip(), json.dumps(salts)))
        inserted += 1

    conn.commit()
    conn.close()

    print(f"✓ Successfully imported {inserted} MD Medicine syllabus drugs into '{DB_FILE}'!")

if __name__ == "__main__":
    seed_database()