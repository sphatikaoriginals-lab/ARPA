import pandas as pd
import re

def clean_brand_name(name):
    if pd.isna(name):
        return ""
    # Convert to string, strip whitespace, and normalize case
    name = str(name).strip()
    # Remove common extra spacing or artifacts
    name = re.sub(r'\s+', ' ', name)
    return name

def process_medicine_dataset(input_filepath, output_filepath, chunk_size=50000):
    """
    Processes large medicine datasets in memory-efficient chunks.
    Expected input columns: 'medicine_name' (or 'name')
    """
    print(f"Starting processing of {input_filepath}...")
    
    # Example dictionary / lookup table for known salts 
    # (In production, replace or merge with your master salt database / SQLite lookup)
    salt_mapping_db = {
        "augmentin 625 duo": "Amoxycillin (500mg) + Clavulanic Acid (125mg)",
        "azithral 500": "Azithromycin (500mg)",
        "combiflam": "Ibuprofen (400mg) + Paracetamol (325mg)",
        "pan d": "Pantoprazole (40id mg) + Domperidone (30mg)",
        "ecosprin 75": "Aspirin (75mg)"
    }

    processed_chunks = []
    
    # Read and process in chunks to handle large files smoothly
    for chunk in pd.read_csv(input_filepath, chunksize=chunk_size, low_memory=False):
        # Identify name column dynamically
        name_col = 'medicine_name' if 'medicine_name' in chunk.columns else chunk.columns[0]
        
        chunk['cleaned_name'] = chunk[name_col].apply(clean_brand_name)
        chunk['lower_name'] = chunk['cleaned_name'].str.lower()
        
        # Map salt compositions using the lookup dictionary
        chunk['salt_composition'] = chunk['lower_name'].map(salt_mapping_db).fillna("Pending Salt Resolution")
        
        # Select final columns for the new sheet
        final_chunk = pd.DataFrame({
            'Medicine Name': chunk['cleaned_name'],
            'Salt Composition': chunk['salt_composition']
        })
        
        processed_chunks.append(final_chunk)
        print(f"Processed chunk of {len(chunk)} rows...")

    # Combine all chunks
    final_df = pd.concat(processed_chunks, ignore_index=True)
    
    # Export to new sheet (CSV or Excel)
    if output_filepath.endswith('.xlsx'):
        final_df.to_excel(output_filepath, index=False, engine='openpyxl')
    else:
        final_df.to_csv(output_filepath, index=False)
        
    print(f"Successfully generated new sheet: {output_filepath} with {len(final_df)} records.")

# Example execution:
# process_medicine_dataset('indian_medicines_datacsv', 'medicines_with_salts.csv', 'all_medicine_with_salt.csv