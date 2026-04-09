import pandas as pd
import re

# --- 1. SETTINGS ---
# Ensure this filename matches your uploaded Excel file
INPUT_FILE = "Untitled spreadsheet (1).xlsx" 
# This must match the exact tab name in your Excel
SHEET_NAME = "Pallet_storage" 
OUTPUT_FILE = "pallet_blueprint.csv"

def generate_pallet_blueprint():
    print(f"Reading {SHEET_NAME} from {INPUT_FILE}...")
    
    # Load the spreadsheet without headers to treat it as a pure grid
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME, header=None)
    
    blueprint_data = []

    # --- 2. THE GRID SCAN ---
    # We iterate through every row (r) and column (c)
    for r in range(df.shape[0]):
        for c in range(df.shape[1]):
            cell_value = str(df.iloc[r, c]).strip()
            
            # We only record cells that aren't empty, NaN, or "None"
            if cell_value and cell_value.lower() != 'nan' and cell_value != 'None':
                
                # Determine the Level based on the prefix (T1, T2, etc.)
                # If the location is 'T2-P-101', we assign it to 'Level 2'
                level = "Level 1" # Default
                if cell_value.startswith("T1"): level = "Level 1"
                elif cell_value.startswith("T2"): level = "Level 2"
                elif cell_value.startswith("T3"): level = "Level 3"
                elif cell_value.startswith("T4"): level = "Level 4"
                elif cell_value.startswith("T5"): level = "Level 5"
                
                blueprint_data.append({
                    'bay_name': cell_value,
                    'grid_row': r,
                    'grid_col': c,
                    'level': level
                })

    # --- 3. SAVE TO CSV ---
    if blueprint_data:
        df_out = pd.DataFrame(blueprint_data)
        df_out.to_csv(OUTPUT_FILE, index=False)
        print(f"✅ Success! {len(blueprint_data)} pallet locations mapped to {OUTPUT_FILE}")
    else:
        print("❌ Error: No location data found in the specified sheet.")

if __name__ == "__main__":
    generate_pallet_blueprint()