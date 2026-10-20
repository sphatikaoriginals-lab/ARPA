import os
import pandas as pd

# File paths ko handle karne ke liye check
input_file = 'all_medicine databased.csv'
if not os.path.exists(input_file):
    # Agar current folder mein nahi hai, toh ek level uphar check karega
    input_file = '../all_medicine databased.csv'

output_file = 'medicines_with_salt_compositions.csv'

print(f"Reading dataset from: {input_file}...")

chunk_size = 50000
chunks = []

for chunk in pd.read_csv(input_file, chunksize=chunk_size, low_memory=False):
    processed = pd.DataFrame()
    processed['Medicine Name'] = chunk['name'].fillna('').str.strip()
    processed['Salt / Chemical Class'] = chunk['Chemical Class'].fillna(chunk['Action Class']).fillna(chunk['substitute0']).fillna('Not Specified')
    processed['Therapeutic Class'] = chunk['Therapeutic Class'].fillna('General')
    processed['Primary Use'] = chunk['use0'].fillna('General')
    chunks.append(processed)
    print(f"Processed chunk of {len(chunk)} rows...")

# Combine and save as new sheet
final_df = pd.concat(chunks, ignore_index=True)
final_df.to_csv(output_file, index=False)
print(f"Successfully generated new sheet: {output_file} with {len(final_df)} records!")