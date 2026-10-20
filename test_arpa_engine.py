import pandas as pd

# Master dataset load karein jo abhi generate kiya hai
df = pd.read_csv('medicines_with_salt_compositions.csv')

def arpa_prescription_audit(brand_name):
    """
    ARPA Engine function to lookup brand name, 
    fetch salt composition/class, and clinical details.
    """
    query = brand_name.strip().lower()
    match = df[df['Medicine Name'].str.lower() == query]
    
    if not match.empty:
        row = match.iloc[0]
        return {
            "Status": "SUCCESS",
            "Medicine Brand": row['Medicine Name'],
            "Salt / Composition": row['Salt / Chemical Class'],
            "Therapeutic Class": row['Therapeutic Class'],
            "Primary Use": row['Primary Use']
        }
    else:
        return {"Status": "NOT_FOUND", "Message": "Brand not found in master database."}

# Test cases testing various categories
test_prescriptions = [
    "augmentin 625 duo tablet",
    "azithral 500 tablet",
    "allegra 120mg tablet",
    "ascoril ls syrup"
]

print("--- ARPA CLINICAL ENGINE BATCH AUDIT TEST ---")
for med in test_prescriptions:
    result = arpa_prescription_audit(med)
    print(f"\nQuery: {med}")
    for k, v in result.items():
        print(f"  {k}: {v}")