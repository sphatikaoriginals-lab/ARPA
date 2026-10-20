import pandas as pd
import os

print("⏳ Loading Medicine Database... This might take a few seconds.")

file_path = os.path.join(os.getcwd(), "medicines.csv")

try:
    # Load the dataset
    df = pd.read_csv(file_path, low_memory=False)
    
    # Standardize column names (different Kaggle datasets have different headers)
    # We will look for standard variations of 'brand' and 'salt'
    cols = [str(c).lower().strip() for c in df.columns]
    df.columns = cols
    
    brand_col = next((c for c in cols if 'name' in c or 'brand' in c), cols[0])
    salt_col = next((c for c in cols if 'salt' in c or 'composition' in c or 'ingredient' in c), cols[1])
    
    # Drop empty rows
    df = df.dropna(subset=[brand_col, salt_col])
    
    print(f"✅ ARPA Database Live: Loaded {len(df):,} medicines!")
    
except Exception as e:
    print(f"❌ Database Error: {e}")
    df = None

def search_medicine_db(query, limit=5):
    """Searches the database for medicines matching the typed/drawn query"""
    if df is None or not query:
        return []
    
    # Search for brands starting with or containing the query (case-insensitive)
    matches = df[df[brand_col].str.contains(query, case=False, na=False)]
    
    results = []
    for _, row in matches.head(limit).iterrows():
        results.append({
            "brand": str(row[brand_col]).title(),
            "salts": str(row[salt_col]).title()
        })
    return results
